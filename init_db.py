import psycopg2
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

def init_db():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    # Создание таблицы для пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL UNIQUE
        )
    ''')

    # Создание таблицы для слов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id SERIAL PRIMARY KEY,
            word TEXT NOT NULL,
            translation TEXT NOT NULL
        )
    ''')

    # Создание таблицы для связи пользователей и слов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_words (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id),
            word_id INTEGER NOT NULL REFERENCES words(id)
        )
    ''')

    # Добавление общих слов, если их еще нет
    common_words = [
        ('красный', 'red'),
        ('синий', 'blue'),
        ('зеленый', 'green'),
        ('желтый', 'yellow'),
        ('черный', 'black'),
        ('белый', 'white'),
        ('он', 'he'),
        ('она', 'she'),
        ('оно', 'it'),
        ('они', 'they')
    ]

    cursor.execute('SELECT COUNT(*) FROM words')
    if cursor.fetchone()[0] == 0:
        for word, translation in common_words:
            cursor.execute(
                'INSERT INTO words (word, translation) VALUES (%s, %s)',
                (word, translation)
            )

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    init_db()