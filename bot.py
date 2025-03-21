import telebot
from db_handlers import *
import logging
from telebot import types
from init_db import init_db

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


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)

# Клавиатура с основными действиями
def create_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_add = types.KeyboardButton('Добавить слово')
    btn_delete = types.KeyboardButton('Удалить слово')
    btn_quiz = types.KeyboardButton('Начать викторину')
    markup.add(btn_add, btn_delete, btn_quiz)
    return markup

# Клавиатура для викторины (с кнопкой "Закончить викторину")
def create_quiz_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_end_quiz = types.KeyboardButton('Закончить викторину')
    markup.add(btn_end_quiz)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    logger.info(f"User {message.from_user.id} started the bot.")
    bot.send_message(
        message.chat.id,
        "Привет! Я бот для изучения английских слов. Выбери действие:",
        reply_markup=create_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == 'Добавить слово')
def add_word_handler(message):
    logger.info(f"User {message.from_user.id} wants to add a word.")
    bot.send_message(message.chat.id, "Введите слово и его перевод в формате: слово перевод")

@bot.message_handler(func=lambda message: message.text == 'Удалить слово')
def delete_word_handler(message):
    logger.info(f"User {message.from_user.id} wants to delete a word.")
    bot.send_message(message.chat.id, "Введите слово, которое хотите удалить:")

@bot.message_handler(func=lambda message: message.text == 'Начать викторину')
def quiz_handler(message):
    logger.info(f"User {message.from_user.id} started a quiz.")
    start_quiz(message)

def start_quiz(message):
    words = get_words_for_quiz(message.from_user.id)
    if not words:
        bot.send_message(message.chat.id, "Нет доступных слов для викторины.")
        return

    # Выбираем случайное слово для вопроса
    question_word, correct_translation = random.choice(words)
    other_translations = [translation for _, translation in words if translation != correct_translation]
    random_translations = random.sample(other_translations, 3)  # 3 случайных неправильных перевода
    all_translations = random_translations + [correct_translation]
    random.shuffle(all_translations)

    # Создаем клавиатуру с вариантами ответов
    markup = create_quiz_keyboard()
    for translation in all_translations:
        markup.add(types.KeyboardButton(translation))

    bot.send_message(message.chat.id, f"Как переводится слово '{question_word}'?", reply_markup=markup)
    bot.register_next_step_handler(message, check_answer, correct_translation)

def check_answer(message, correct_translation):
    if message.text == 'Закончить викторину':
        bot.send_message(
            message.chat.id,
            "Викторина завершена. Возвращаюсь в главное меню.",
            reply_markup=create_main_keyboard()
        )
        return

    if message.text == correct_translation:
        bot.send_message(message.chat.id, "Правильно! 🎉")
    else:
        bot.send_message(message.chat.id, f"Неправильно. Правильный ответ: {correct_translation}.")

    # Продолжаем викторину
    start_quiz(message)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if len(message.text.split()) == 2:  # Добавление слова
        word, translation = message.text.split()
        add_user_word(message.from_user.id, word, translation)
        logger.info(f"User {message.from_user.id} added word: {word} -> {translation}")
        bot.send_message(message.chat.id, f"Слово '{word}' с переводом '{translation}' добавлено.")
    elif len(message.text.split()) == 1:  # Удаление слова
        word = message.text
        delete_user_word(message.from_user.id, word)
        logger.info(f"User {message.from_user.id} deleted word: {word}")
        bot.send_message(message.chat.id, f"Слово '{word}' удалено.")
    else:
        bot.send_message(message.chat.id, "Не понимаю команду. Используйте кнопки или введите данные в правильном формате.")

if __name__ == "__main__":
    init_db()
    logger.info("Bot started polling.")
    bot.polling()