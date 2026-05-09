import os
import psycopg2
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")
conn.autocommit = True

cursor = conn.cursor()


# таблица пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS video_cache (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE,
    file_id TEXT,
    audio_file_id TEXT,
    platform TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def add_user(user_id, username=None, first_name=None):
    now = datetime.utcnow()

    cursor.execute("""
    INSERT INTO users (user_id, username, first_name, first_seen, last_seen)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (user_id)
    DO UPDATE SET
        username = EXCLUDED.username,
        first_name = EXCLUDED.first_name,
        last_seen = EXCLUDED.last_seen
    """, (user_id, username, first_name, now, now))

def get_users(offset=0, limit=10):
    cursor.execute("""
        SELECT user_id, username, first_name
        FROM users
        ORDER BY last_seen DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))

    return cursor.fetchall()

def get_users_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]
    
def add_event(user_id, url, platform, status="pending"):
    cursor.execute("""
        INSERT INTO events (user_id, url, platform, status)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (user_id, url, platform, status))

    event_id = cursor.fetchone()[0]
    conn.commit()

    return event_id


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
    
def get_user(user_id):
    cursor.execute("""
    SELECT user_id, username, first_name
    FROM users
    WHERE user_id = %s
    """, (user_id,))

    return cursor.fetchone()
    
def get_user_total_events(user_id):
    cursor.execute("""
    SELECT COUNT(*)
    FROM events
    WHERE user_id = %s
    """, (user_id,))

    return cursor.fetchone()[0]

def get_user_success_events(user_id):
    cursor.execute("""
    SELECT COUNT(*)
    FROM events
    WHERE user_id = %s
    AND status = 'success'
    """, (user_id,))

    return cursor.fetchone()[0]

def get_user_error_events(user_id):
    cursor.execute("""
    SELECT COUNT(*)
    FROM events
    WHERE user_id = %s
    AND status = 'error'
    """, (user_id,))

    return cursor.fetchone()[0]
    
def get_cached_video(url):
    cursor.execute("""
        SELECT file_id, audio_file_id
        FROM video_cache
        WHERE url = %s
    """, (url,))

    return cursor.fetchone()


def save_cached_video(url, file_id, audio_file_id, platform):
    cursor.execute("""
        INSERT INTO video_cache
        (url, file_id, audio_file_id, platform)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (url)
        DO UPDATE SET
            file_id = EXCLUDED.file_id,
            audio_file_id = EXCLUDED.audio_file_id
    """, (url, file_id, audio_file_id, platform))

    conn.commit()
