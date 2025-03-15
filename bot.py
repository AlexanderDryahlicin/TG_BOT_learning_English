import random
import psycopg2
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
import os
from dotenv import load_dotenv
# Загружаем переменные окружения из файла .env
load_dotenv()

# Параметры подключения к базе данных
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
TOKEN = os.getenv("TOKEN")

# Настройки подключения к базе данных
DB_CONFIG = {
    'dbname': DB_NAME,  # Имя базы данных
    'user': DB_USER,  # Имя пользователя
    'password': DB_PASSWORD,  # Пароль
    'host': DB_HOST,  # Хост
    'port': DB_PORT  # Порт
}

# Инициализация бота
state_storage = StateMemoryStorage()
bot = TeleBot(TOKEN, state_storage=state_storage)

# Состояния для FSM (Finite State Machine)
class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()

# Команды для кнопок
class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'

# Подключение к базе данных
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# Получение случайного слова из базы данных
def get_random_word(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Получаем случайное слово, которое пользователь еще не изучал
        cursor.execute('''
            SELECT w.word_id, w.word, w.translation
            FROM words w
            WHERE w.word_id NOT IN (
                SELECT uw.word_id
                FROM user_words uw
                WHERE uw.user_id = %s
            )
            ORDER BY RANDOM()
            LIMIT 1
        ''', (user_id,))
        word = cursor.fetchone()
        return word
    finally:
        cursor.close()
        conn.close()

# Получение других слов для вариантов ответа
def get_other_words(word_id, count=4):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT word
            FROM words
            WHERE word_id != %s
            ORDER BY RANDOM()
            LIMIT %s
        ''', (word_id, count))
        words = cursor.fetchall()
        return [row[0] for row in words]
    finally:
        cursor.close()
        conn.close()

# Добавление слова в изученные для пользователя
def add_user_word(user_id, word_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO user_words (user_id, word_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, word_id) DO NOTHING
        ''', (user_id, word_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# Удаление слова из изученных для пользователя
def delete_user_word(user_id, word_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            DELETE FROM user_words
            WHERE user_id = %s AND word_id = %s
        ''', (user_id, word_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# Обработчик команды /start и /cards
@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Добавляем пользователя в базу данных, если его еще нет
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (user_id, username)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO NOTHING
        ''', (user_id, username))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    # Получаем случайное слово
    word = get_random_word(user_id)
    if not word:
        bot.send_message(message.chat.id, "Вы изучили все слова! Добавьте новые слова.")
        return

    # Получаем другие слова для вариантов ответа
    other_words = get_other_words(word[0])

    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = [types.KeyboardButton(word[1])]  # word[1] - слово на английском
    buttons.extend(types.KeyboardButton(w) for w in other_words)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    markup.add(*buttons)

    # Отправляем сообщение с вопросом
    greeting = f"Выбери перевод слова:\n🇷🇺 {word[2]}"  # word[2] - перевод
    bot.send_message(message.chat.id, greeting, reply_markup=markup)

    # Сохраняем состояние
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = word[1]  # word[1] - слово на английском
        data['translate_word'] = word[2]  # word[2] - перевод
        data['word_id'] = word[0]  # word[0] - word_id

# Обработчик кнопки "Дальше ⏭"
@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)

# Обработчик кнопки "Добавить слово ➕"
@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    bot.send_message(message.chat.id, "Введите слово и его перевод через пробел (например: Apple Яблоко):")
    bot.register_next_step_handler(message, process_add_word)

def process_add_word(message):
    try:
        word, translation = message.text.split(maxsplit=1)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO words (word, translation)
                VALUES (%s, %s)
                ON CONFLICT (word) DO NOTHING
            ''', (word, translation))
            conn.commit()
            bot.send_message(message.chat.id, f"Слово '{word}' добавлено в базу данных.")
        finally:
            cursor.close()
            conn.close()
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат. Пожалуйста, введите слово и его перевод через пробел.")

# Обработчик кнопки "Удалить слово🔙"
@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        word_id = data['word_id']
        delete_user_word(message.from_user.id, word_id)
        bot.send_message(message.chat.id, f"Слово '{data['target_word']}' удалено из вашего списка изученных.")

# Обработчик текстовых сообщений (проверка ответа)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if text == data['target_word']:
            add_user_word(message.from_user.id, data['word_id'])
            hint = f"Отлично!❤\n{data['target_word']} -> {data['translate_word']}"
        else:
            hint = f"Допущена ошибка!\nПопробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}"
    bot.send_message(message.chat.id, hint)

# Запуск бота
if __name__ == '__main__':
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.infinity_polling(skip_pending=True)