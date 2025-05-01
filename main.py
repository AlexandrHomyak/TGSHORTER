import telebot
import sqlite3
import pyshorteners
import requests
import json
import time

URL_SCAN_ENDPOINT = "https://www.virustotal.com/api/v3/urls"
API_KEY = "YOUR_API_KEY"  # Replace with your actual API key

# Replace 'YOUR_BOT_TOKEN' with your Telegram bot token
BOT_TOKEN = 'YOUR_BOT_TOKEN'

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize the link shortener
s = pyshorteners.Shortener()  # Uses tinyurl service by default

# --- Database functions ---

def create_table():
    """Creates the 'links' table in the database if it doesn't exist."""
    conn = sqlite3.connect('links.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            original_link TEXT,
            shortened_link TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_link(user_id, original_link, shortened_link):
    """Inserts a link into the database."""
    conn = sqlite3.connect('links.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO links (user_id, original_link, shortened_link)
        VALUES (?, ?, ?)
    ''', (user_id, original_link, shortened_link))
    conn.commit()
    conn.close()

def get_links_by_user(user_id):
    """Retrieves all links for a user from the database."""
    conn = sqlite3.connect('links.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT original_link, shortened_link FROM links
        WHERE user_id = ?
    ''', (user_id,))
    links = cursor.fetchall()
    conn.close()
    return links

# --- Bot command handlers ---

@bot.message_handler(commands=['start'])
def start(message):
    """Handles the /start command. Greets the user."""
    bot.reply_to(message, "Hello! I'm a link shortening bot. Send me a link, and I'll shorten it.")
    create_table()  # Create the table if it doesn't exist

@bot.message_handler(commands=['links'])
def show_links(message):
    """Handles the /links command. Shows all shortened links for the user."""
    user_id = message.from_user.id
    links = get_links_by_user(user_id)
    if links:
        response = "Your shortened links:\n"
        for original_link, shortened_link in links:
            response += f"Original: {original_link}\nShortened: {shortened_link}\n\n"
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "You don't have any shortened links yet.")


@bot.message_handler(commands=['shortlink'])
def shorten_link(message):
    bot.reply_to(message, 'Send the link you want to shorten')
    @bot.message_handler(func=lambda message: True)
    def shorting(message):
      """Handles text messages (assumed to be links)."""
      original_link = message.text
      user_id = message.from_user.id

      try:
          if not original_link.startswith("http"):
              raise ValueError("Invalid URL format")
          else:
              shortened_link = s.tinyurl.short(original_link)  # Use tinyurl
              bot.reply_to(message, f"Shortened link: {shortened_link}")
              insert_link(user_id, original_link, shortened_link)
      except Exception as e:
          bot.reply_to(message, f"An error occurred while shortening the link: {e}")  # Report the error
          print(f"Error shortening link: {e}") # Log the error for debugging

@bot.message_handler(commands=['check'])
def check_link(message):
  bot.reply_to(message, "Send me the link you want to check")
  bot.register_next_step_handler(message, check)
def check(message):
  url = message.text
  HEADERS = {
  "accept": "application/json",
  "x-apikey": API_KEY
  }

  def scan_url(url):
    payload = {"url": url}
    headers_post = HEADERS.copy()
    headers_post["content-type"] = "application/x-www-form-urlencoded"

    try:
      response = requests.post(URL_SCAN_ENDPOINT, data=payload, headers=headers_post)
      response.raise_for_status()
      submission_data = response.json()
      analysis_id = submission_data["data"]["id"]
      return analysis_id

    except requests.exceptions.RequestException as e:
      bot.reply_to(message, f"Error submitting URL: {e}")
      print(f"Error submitting URL: {e}")
      return None
    except (KeyError, json.JSONDecodeError) as e:
        bot.reply_to(message, f"Error processing the response: {e}")
        print(f"Error parsing submission response: {e}")
        return None

  ANALYSIS_URL = "https://www.virustotal.com/api/v3/analyses/" # Define analysis URL

  def get_analysis_results(analysis_id):
      """Polls the VirusTotal API until the analysis is completed."""
      max_retries = 10 # Adjust as needed
      delay = 5        # Adjust as needed (seconds)

      for attempt in range(max_retries):
        try:
          analysis_url = f"{ANALYSIS_URL}{analysis_id}" # Build URL
          response = requests.get(analysis_url, headers=HEADERS)
          response.raise_for_status()
          analysis_data = response.json()

          # Check if the analysis is complete (status should be 'completed')
          status = analysis_data.get("data", {}).get("attributes", {}).get("status")
          if status == "completed":
            return analysis_data  # Analysis is complete, return the results

          bot.reply_to(message, f"Analysis is not yet complete. Attempt {attempt + 1}/{max_retries}. Waiting...")
          print(f"Analysis not completed yet. Attempt {attempt + 1}/{max_retries}. Waiting...")
          time.sleep(delay)  # Wait before retrying

        except requests.exceptions.RequestException as e:
          bot.reply_to(message, f"Error retrieving analysis results: {e}")
          print(f"Error retrieving analysis results: {e}")
          return None
        except (KeyError, json.JSONDecodeError) as e:
          bot.reply_to(message, f"Error processing the response with results: {e}")
          print(f"Error parsing analysis response: {e}")
          return None

      bot.reply_to(message, "Failed to retrieve analysis results after several attempts.")
      print("Failed to retrieve analysis results after multiple attempts.")
      return None # Return None if max retries are reached


  def generate_report(analysis_data):
      if not analysis_data:
        return "No data for analysis."

      attributes = analysis_data.get("data", {}).get("attributes", {})
      stats = attributes.get("stats", {})
      total_scans = sum(stats.values())

      report = f"""
      --- VirusTotal Scan Report ---
      URL: {url}
      Total scans: {total_scans}
      Harmless detections: {stats.get('harmless', 0)}
      Malicious detections: {stats.get('malicious', 0)}
      Suspicious detections: {stats.get('suspicious', 0)}
      Undetected detections: {stats.get('undetected', 0)}
      Timeout detections: {stats.get('timeout', 0)}
      """

      return report

  analysis_id = scan_url(url)

  if analysis_id:
      results = get_analysis_results(analysis_id)  # Get analysis results, polling until complete
      if results:
        report = generate_report(results)
        bot.reply_to(message, report)
      else:
        bot.reply_to(message, "Failed to retrieve scan results.")
  else:
      bot.reply_to(message, "Failed to submit URL for scanning.")




# --- Start the bot ---

if __name__ == '__main__':
    print("Bot started...")
    bot.infinity_polling()
