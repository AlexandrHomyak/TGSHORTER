import telebot
import sqlite3
import pyshorteners

# Replace 'YOUR_BOT_TOKEN' with your Telegram bot token
BOT_TOKEN = 'YOUR_BOT_TOKEN'

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize the URL shortener
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
    bot.reply_to(message, "Hello! I'm a link shortening bot. Send me a link and I'll shorten it for you.")
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


@bot.message_handler(func=lambda message: True)
def shorten_link(message):
    """Handles all text messages (assumes they are links)."""
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
        bot.reply_to(message, e)  # Report the error
        print(f"Error shortening link: {e}") # Log the error for debugging

# --- Run the bot ---

if __name__ == '__main__':
    print("Bot started...")
    bot.infinity_polling()
