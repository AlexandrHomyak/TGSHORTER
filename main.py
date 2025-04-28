import telebot
import sqlite3
import pyshorteners

# Замените 'YOUR_BOT_TOKEN' на токен вашего Telegram-бота
BOT_TOKEN = 'YOUR_BOT_TOKEN'

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Инициализация сокращателя ссылок
s = pyshorteners.Shortener()  # Используется сервис tinyurl по умолчанию

# --- Функции для работы с базой данных ---

def create_table():
    """Создает таблицу links в базе данных, если она не существует."""
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
    """Вставляет ссылку в базу данных."""
    conn = sqlite3.connect('links.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO links (user_id, original_link, shortened_link)
        VALUES (?, ?, ?)
    ''', (user_id, original_link, shortened_link))
    conn.commit()
    conn.close()

def get_links_by_user(user_id):
    """Получает все ссылки пользователя из базы данных."""
    conn = sqlite3.connect('links.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT original_link, shortened_link FROM links
        WHERE user_id = ?
    ''', (user_id,))
    links = cursor.fetchall()
    conn.close()
    return links

# --- Обработчики команд бота ---

@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start.  Приветствует пользователя."""
    bot.reply_to(message, "Привет! Я бот для сокращения ссылок. Отправьте мне ссылку, и я ее сокращу.")
    create_table()  # Создаем таблицу, если ее нет

@bot.message_handler(commands=['links'])
def show_links(message):
    """Обработчик команды /links.  Показывает все сокращенные ссылки пользователя."""
    user_id = message.from_user.id
    links = get_links_by_user(user_id)
    if links:
        response = "Ваши сокращенные ссылки:\n"
        for original_link, shortened_link in links:
            response += f"Оригинальная: {original_link}\nСокращенная: {shortened_link}\n\n"
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "У вас пока нет сокращенных ссылок.")


@bot.message_handler(func=lambda message: True)
def shorten_link(message):
    """Обработчик всех текстовых сообщений (предполагается, что это ссылки)."""
    original_link = message.text
    user_id = message.from_user.id

    try:
        if not original_link.startswith("http"):
            raise ValueError("Invalid URL format")
        else:
            shortened_link = s.tinyurl.short(original_link)  # Используем tinyurl
            bot.reply_to(message, f"Сокращенная ссылка: {shortened_link}")
            insert_link(user_id, original_link, shortened_link)
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка при сокращении ссылки: {e}")  # Сообщаем об ошибке
        print(f"Ошибка при сокращении ссылки: {e}") # Логируем ошибку для отладки

# --- Запуск бота ---

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
