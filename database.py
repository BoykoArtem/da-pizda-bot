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