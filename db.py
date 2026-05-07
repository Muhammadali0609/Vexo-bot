import sqlite3
from datetime import datetime

# создаём файл базы
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

# таблица пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_seen TEXT,
    last_seen TEXT
)
""")

conn.commit()


# добавить / обновить пользователя
def add_user(user_id: int):
    now = datetime.utcnow().isoformat()

    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, first_seen, last_seen)
    VALUES (?, ?, ?)
    """, (user_id, now, now))

    cursor.execute("""
    UPDATE users SET last_seen = ?
    WHERE user_id = ?
    """, (now, user_id))

    conn.commit()


# получить количество пользователей
def get_users_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]