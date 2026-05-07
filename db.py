import os
import psycopg2
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

cursor = conn.cursor()

# таблица пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    url TEXT,
    platform TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
""")

def add_user(user_id: int):
    now = datetime.utcnow()

    cursor.execute("""
    INSERT INTO users (user_id, first_seen, last_seen)
    VALUES (%s, %s, %s)
    ON CONFLICT (user_id)
    DO UPDATE SET last_seen = EXCLUDED.last_seen
    """, (user_id, now, now))


def get_users_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]