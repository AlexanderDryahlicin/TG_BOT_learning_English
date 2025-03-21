import psycopg2
import random
import logging
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

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def add_user_word(user_id, word, translation):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Добавляем пользователя, если его еще нет
        cursor.execute('INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING', (user_id,))

        # Добавляем слово в таблицу words
        cursor.execute('INSERT INTO words (word, translation) VALUES (%s, %s) RETURNING id', (word, translation))
        word_id = cursor.fetchone()[0]

        # Связываем слово с пользователем
        cursor.execute('INSERT INTO user_words (user_id, word_id) VALUES (%s, %s)', (user_id, word_id))

        conn.commit()
        logger.info(f"User {user_id} added word: {word} -> {translation}")
    except Exception as e:
        logger.error(f"Error adding word: {e}")
    finally:
        cursor.close()
        conn.close()

def delete_user_word(user_id, word):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Находим ID слова
        cursor.execute('SELECT id FROM words WHERE word = %s', (word,))
        word_id = cursor.fetchone()

        if word_id:
            # Удаляем связь пользователя с этим словом
            cursor.execute(
                'DELETE FROM user_words WHERE user_id = %s AND word_id = %s',
                (user_id, word_id[0])
            )

            # Проверяем, есть ли другие пользователи, связанные с этим словом
            cursor.execute('SELECT COUNT(*) FROM user_words WHERE word_id = %s', (word_id[0],))
            remaining_users = cursor.fetchone()[0]

            # Если больше никто не использует это слово, удаляем его из таблицы words
            if remaining_users == 0:
                cursor.execute('DELETE FROM words WHERE id = %s', (word_id[0],))

            conn.commit()
            logger.info(f"User {user_id} deleted word: {word}")
        else:
            logger.warning(f"Word '{word}' not found in the database.")
    except Exception as e:
        logger.error(f"Error deleting word: {e}")
    finally:
        cursor.close()
        conn.close()

def get_words_for_quiz(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Выбираем слова, которые либо общие, либо принадлежат текущему пользователю
        cursor.execute('''
            SELECT w.word, w.translation FROM words w
            LEFT JOIN user_words uw ON w.id = uw.word_id
            WHERE uw.user_id = %s OR uw.user_id IS NULL
            ORDER BY RANDOM()
            LIMIT 4
        ''', (user_id,))
        words = cursor.fetchall()
        return words
    except Exception as e:
        logger.error(f"Error fetching words for quiz: {e}")
        return []
    finally:
        cursor.close()
        conn.close()