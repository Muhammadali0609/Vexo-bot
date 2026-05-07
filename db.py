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
    
def add_event(user_id, url, platform, status="pending"):
    cursor.execute("""
        INSERT INTO events (user_id, url, platform, status)
        VALUES (%s, %s, %s, %s)
    """, (user_id, url, platform, status))


def update_event_status(event_id, status):
    cursor.execute("""
        UPDATE events
        SET status = %s
        WHERE id = %s
    """, (status, event_id))
    
def get_total_events():
    cursor.execute("SELECT COUNT(*) FROM events")
    return cursor.fetchone()[0]


def get_today_events():
    cursor.execute("""
        SELECT COUNT(*) FROM events
        WHERE created_at >= NOW() - INTERVAL '1 day'
    """)
    return cursor.fetchone()[0]


def get_success_count():
    cursor.execute("""
        SELECT COUNT(*) FROM events
        WHERE status = 'success'
    """)
    return cursor.fetchone()[0]


def get_error_count():
    cursor.execute("""
        SELECT COUNT(*) FROM events
        WHERE status = 'error'
    """)
    return cursor.fetchone()[0]