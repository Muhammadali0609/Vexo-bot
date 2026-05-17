import os
import psycopg2
from datetime import datetime
import json
from psycopg2.extras import Json

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL is missing")

    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    conn = get_conn()
    try:
        cursor = conn.cursor()

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
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'ru'
        """)
        
        cursor.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE
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
        CREATE TABLE IF NOT EXISTS media_cache (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE,
            media_type TEXT NOT NULL,
            items JSONB NOT NULL,
            platform TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
        conn.commit()
    finally:
        conn.close()

def add_user(user_id, username=None, first_name=None):
    conn = get_conn()
    try:
        cursor = conn.cursor()
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
        conn.commit()
    finally:
        conn.close()

def get_users(offset=0, limit=10):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, first_name, first_seen, last_seen
            FROM users
            ORDER BY last_seen DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
    
        return cursor.fetchall()
    finally:
        conn.close()

def get_users_count():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]
    finally:
        conn.close()
    
def add_event(user_id, url, platform, status="pending"):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (user_id, url, platform, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_id, url, platform, status))
    
        event_id = cursor.fetchone()[0]
        conn.commit()
    
        return event_id
    finally:
        conn.close()


def update_event_status(event_id, status):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE events
            SET status = %s
            WHERE id = %s
        """, (status, event_id))
        conn.commit()
    finally:
        conn.close()
    
def get_total_events():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_today_events():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM events
            WHERE created_at >= NOW() - INTERVAL '1 day'
        """)
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_success_count():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM events
            WHERE status = 'success'
        """)
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_error_count():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM events
            WHERE status = 'error'
        """)
        return cursor.fetchone()[0]
    finally:
        conn.close()
    
def get_user(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT user_id, username, first_name, first_seen, last_seen
        FROM users
        WHERE user_id = %s
        """, (user_id,))
    
        return cursor.fetchone()
    finally:
        conn.close()
    
def get_user_total_events(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(*)
        FROM events
        WHERE user_id = %s
        """, (user_id,))
    
        return cursor.fetchone()[0]
    finally:
        conn.close()

def get_user_success_events(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(*)
        FROM events
        WHERE user_id = %s
        AND status = 'success'
        """, (user_id,))
    
        return cursor.fetchone()[0]
    finally:
        conn.close()

def get_user_error_events(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT COUNT(*)
        FROM events
        WHERE user_id = %s
        AND status = 'error'
        """, (user_id,))
    
        return cursor.fetchone()[0]
    finally:
        conn.close()
    
def get_cached_video(url):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT file_id, audio_file_id
            FROM video_cache
            WHERE url = %s
        """, (url,))
    
        return cursor.fetchone()
    finally:
        conn.close()


def save_cached_video(url, file_id, audio_file_id, platform):
    conn = get_conn()
    try:
        cursor = conn.cursor()
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
    finally:
        conn.close()

def get_cached_media(url):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT media_type, items
            FROM media_cache
            WHERE url = %s
        """, (url,))
        row = cursor.fetchone()

        if not row:
            return None

        media_type, items = row
        if isinstance(items, str):
            items = json.loads(items)

        return media_type, items
    finally:
        conn.close()


def save_cached_media(url, media_type, items, platform):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO media_cache (url, media_type, items, platform)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (url)
            DO UPDATE SET
                media_type = EXCLUDED.media_type,
                items = EXCLUDED.items,
                platform = EXCLUDED.platform,
                updated_at = CURRENT_TIMESTAMP
        """, (url, media_type, Json(items), platform))
        conn.commit()
    finally:
        conn.close()

def set_user_lang(user_id, lang):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET language=%s WHERE user_id=%s",
            (lang, user_id)
        )
        conn.commit()
    finally:
        conn.close()

def get_user_lang(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT language FROM users WHERE user_id=%s",
            (user_id,)
        )
        row = cursor.fetchone()
    
        if row:
            return row[0]
    
        return "ru"
    finally:
        conn.close()

def is_user_banned(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_banned FROM users WHERE user_id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return row[0]
        return False
    finally:
        conn.close()
        
def ban_user(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_banned = TRUE WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()
    finally:
        conn.close()
        
def unban_user(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_banned = FALSE WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()
    finally:
        conn.close()
