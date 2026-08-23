import sqlite3
import random

DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            first_name TEXT,
            beauty_count INTEGER DEFAULT 0,
            is_bot INTEGER DEFAULT 0,
            birthdate TEXT,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN birthdate TEXT")
    except sqlite3.OperationalError:
        pass
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pizda_candidates (
        chat_id INTEGER,
        message_id INTEGER,
        created_at INTEGER,
        used INTEGER DEFAULT 0,
        PRIMARY KEY (chat_id, message_id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    conn.commit()
    conn.close()

def save_or_update_user(user, chat_id: int):
    if user.is_bot:
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    username = f"@{user.username}" if user.username else user.first_name
    cursor.execute("""
        INSERT INTO users (user_id, chat_id, username, first_name, beauty_count, is_bot)
        VALUES (?, ?, ?, ?, 0, 0)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
    """, (user.id, chat_id, username, user.first_name))
    conn.commit()
    conn.close()

def save_custom_birthdate(chat_id: int, username: str, bday_str: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    formatted_username = username if username.startswith("@") else f"@{username}"
    cursor.execute("""
        UPDATE users 
        SET birthdate = ? 
        WHERE chat_id = ? AND LOWER(username) = LOWER(?)
    """, (bday_str, chat_id, formatted_username))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def get_user_birthdate_from_db(user_id: int, chat_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT birthdate FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def pick_beauty_of_the_day(chat_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, beauty_count FROM users WHERE chat_id = ? AND is_bot = 0", (chat_id,))
    users = cursor.fetchall()
    if not users:
        conn.close()
        return None

    winner = random.choice(users)
    user_id, username, count = winner
    new_count = count + 1
    cursor.execute("UPDATE users SET beauty_count = ? WHERE user_id = ? AND chat_id = ?", (new_count, user_id, chat_id))
    conn.commit()
    conn.close()
    return username, new_count

def get_top_beauties(chat_id: int, limit: int = 3):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, beauty_count 
        FROM users 
        WHERE chat_id = ? AND is_bot = 0 AND beauty_count > 0
        ORDER BY beauty_count DESC 
        LIMIT ?
    """, (chat_id, limit))
    top_users = cursor.fetchall()
    conn.close()
    return top_users

def get_all_chats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT chat_id FROM users")
    chats = cursor.fetchall()
    conn.close()
    return chats

def save_pizda_candidate(chat_id: int, message_id: int, created_at: int, used: int = 0):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO pizda_candidates (chat_id, message_id, created_at, used)
        VALUES (?, ?, ?, ?)
    """, (chat_id, message_id, created_at, used))
    inserted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return inserted

def mark_pizda_candidate_used(chat_id: int, message_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE pizda_candidates SET used = 1 WHERE chat_id = ? AND message_id = ?",
        (chat_id, message_id),
    )
    conn.commit()
    conn.close()

def get_pizda_candidate_chats(before_ts: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT chat_id
        FROM pizda_candidates
        WHERE used = 0 AND created_at < ?
    """, (before_ts,))
    chats = cursor.fetchall()
    conn.close()
    return chats

def get_all_pizda_candidates():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT chat_id, message_id, created_at, used FROM pizda_candidates"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "created_at": created_at,
            "used": used,
        }
        for chat_id, message_id, created_at, used in rows
    ]

def pick_pizda_candidates(chat_id: int, before_ts: int, limit: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message_id
        FROM pizda_candidates
        WHERE chat_id = ? AND used = 0 AND created_at < ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (chat_id, before_ts, limit))
    rows = cursor.fetchall()
    conn.close()
    return [message_id for (message_id,) in rows]

def get_bot_meta(key: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM bot_meta WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_bot_meta(key: str, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if value is None:
        cursor.execute("DELETE FROM bot_meta WHERE key = ?", (key,))
    else:
        cursor.execute("""
            INSERT INTO bot_meta (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))
    conn.commit()
    conn.close()