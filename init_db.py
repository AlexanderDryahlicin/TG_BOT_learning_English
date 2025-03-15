import asyncpg
import asyncio
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



# Настройки подключения к базе данных
DB_CONFIG = {
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME,
    'host': DB_HOST,
    'port': DB_PORT,
}

# SQL-запросы для создания таблиц
CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT
);

CREATE TABLE IF NOT EXISTS words (
    word_id SERIAL PRIMARY KEY,
    word TEXT NOT NULL,
    translation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_words (
    user_id BIGINT REFERENCES users(user_id),
    word_id INT REFERENCES words(word_id),
    PRIMARY KEY (user_id, word_id)
);
"""

# Добавление уникального ограничения на столбец `word`
ADD_UNIQUE_CONSTRAINT = """
ALTER TABLE words ADD CONSTRAINT words_word_unique UNIQUE (word);
"""

# Начальные данные для таблицы `words`
INITIAL_WORDS = [
    ("красный", "red"),
    ("синий", "blue"),
    ("зеленый", "green"),
    ("я", "I"),
    ("ты", "you"),
    ("он", "he"),
    ("она", "she"),
    ("оно", "it"),
    ("мы", "we"),
    ("они", "they")
]

async def init_db():
    conn = None
    try:
        # Подключение к базе данных
        conn = await asyncpg.connect(**DB_CONFIG)
        print("Подключение к базе данных успешно установлено.")

        # Создание таблиц
        await conn.execute(CREATE_TABLES)
        print("Таблицы успешно созданы (или уже существовали).")

        # Добавление уникального ограничения, если его нет
        try:
            await conn.execute(ADD_UNIQUE_CONSTRAINT)
            print("Уникальное ограничение на столбец `word` добавлено.")
        except asyncpg.exceptions.DuplicateObjectError:
            print("Уникальное ограничение на столбец `word` уже существует.")

        # Заполнение таблицы `words` начальными данными
        for word, translation in INITIAL_WORDS:
            await conn.execute('''
                INSERT INTO words (word, translation) VALUES ($1, $2)
                ON CONFLICT (word) DO NOTHING
            ''', word, translation)
        print("Начальные данные успешно добавлены в таблицу `words`.")

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        # Закрытие соединения с базой данных
        if conn:
            await conn.close()
            print("Соединение с базой данных закрыто.")

# Запуск инициализации базы данных
if __name__ == '__main__':
    asyncio.run(init_db())