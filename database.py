import sqlite3
import random
from datetime import datetime
import pytz
from config import DUEL_TIMEZONE

DB_NAME = "bot_database.db"


def _get_today_date_str() -> str:
    """Возвращает текущую дату в формате YYYY-MM-DD с учетом выбранного часового пояса."""
    tz = pytz.timezone(DUEL_TIMEZONE)
    return datetime.now(tz).strftime("%Y-%m-%d")


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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS duel_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            display_name TEXT NOT NULL,
            points INTEGER DEFAULT 20,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            stolen_dicks_count INTEGER DEFAULT 0,
            dick_stolen_count INTEGER DEFAULT 0,
            dick_stolen_today INTEGER DEFAULT 0,
            last_activity_date TEXT,
            last_stolen_by TEXT DEFAULT NULL
        )
    """)

    try:
        cursor.execute("ALTER TABLE duel_users ADD COLUMN stolen_dicks_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE duel_users ADD COLUMN last_stolen_by TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# ==========================================
# 🗡️ ЛОГИКА ДУЭЛЕЙ
# ==========================================

def _clean_name(name: str | None) -> str:
    """Удаляет символ @ из имени для предотвращения пушей и тегов."""
    if not name:
        return "Гном"
    return name.lstrip("@")


def _reset_user_if_new_day(cursor, row):
    """Сбрасывает дневные лимиты/очки, если наступил новый день."""
    if not row:
        return None

    today_str = _get_today_date_str()
    (
        user_id, username, display_name, points, wins, losses,
        stolen_dicks_count, dick_stolen_count, dick_stolen_today,
        last_activity_date, last_stolen_by
    ) = row

    if last_activity_date != today_str:
        points = 20
        dick_stolen_today = 0
        last_stolen_by = None
        last_activity_date = today_str
        cursor.execute("""
            UPDATE duel_users
            SET points = 20, dick_stolen_today = 0, last_stolen_by = NULL, last_activity_date = ?
            WHERE user_id = ?
        """, (today_str, user_id))

    return {
        "user_id": user_id,
        "username": _clean_name(username),
        "display_name": _clean_name(display_name),
        "points": points,
        "wins": wins,
        "losses": losses,
        "stolen_dicks_count": stolen_dicks_count,
        "dick_stolen_count": dick_stolen_count,
        "dick_stolen_today": bool(dick_stolen_today),
        "last_activity_date": last_activity_date,
        "last_stolen_by": _clean_name(last_stolen_by) if last_stolen_by else None
    }


def get_or_create_duel_user(conn: sqlite3.Connection, tg_user) -> dict:
    """Получает или создает пользователя дуэлей."""
    cursor = conn.cursor()
    display_name = _clean_name(tg_user.first_name)
    username = _clean_name(tg_user.username)

    cursor.execute("""
        SELECT user_id, username, display_name, points, wins, losses,
               stolen_dicks_count, dick_stolen_count, dick_stolen_today,
               last_activity_date, last_stolen_by
        FROM duel_users WHERE user_id = ?
    """, (tg_user.id,))
    row = cursor.fetchone()

    if not row and username:
        cursor.execute("""
            SELECT user_id, username, display_name, points, wins, losses,
                   stolen_dicks_count, dick_stolen_count, dick_stolen_today,
                   last_activity_date, last_stolen_by
            FROM duel_users WHERE LOWER(username) = LOWER(?)
        """, (username,))
        row = cursor.fetchone()

        if row:
            temp_user_id = row[0]
            cursor.execute("""
                UPDATE duel_users 
                SET user_id = ?, username = ?, display_name = ? 
                WHERE user_id = ?
            """, (tg_user.id, username, display_name, temp_user_id))
            row = (tg_user.id, username, display_name) + row[3:]

    if not row:
        today_str = _get_today_date_str()
        cursor.execute("""
            INSERT INTO duel_users (user_id, username, display_name, points, wins, losses, stolen_dicks_count, dick_stolen_count, dick_stolen_today, last_activity_date, last_stolen_by)
            VALUES (?, ?, ?, 20, 0, 0, 0, 0, 0, ?, NULL)
        """, (tg_user.id, username, display_name, today_str))
        conn.commit()
        return {
            "user_id": tg_user.id,
            "username": username,
            "display_name": display_name,
            "points": 20,
            "wins": 0,
            "losses": 0,
            "stolen_dicks_count": 0,
            "dick_stolen_count": 0,
            "dick_stolen_today": False,
            "last_activity_date": today_str,
            "last_stolen_by": None
        }

    if row[1] != username or row[2] != display_name:
        cursor.execute("""
            UPDATE duel_users SET username = ?, display_name = ? WHERE user_id = ?
        """, (username, display_name, tg_user.id))

    res = _reset_user_if_new_day(cursor, row)
    conn.commit()
    return res


def get_duel_user_by_username(username: str) -> dict | None:
    """Поиск дуэлянта по нику без знака @."""
    clean_username = _clean_name(username)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, username, display_name, points, wins, losses,
               stolen_dicks_count, dick_stolen_count, dick_stolen_today,
               last_activity_date, last_stolen_by
        FROM duel_users WHERE LOWER(username) = LOWER(?)
    """, (clean_username,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    res = _reset_user_if_new_day(cursor, row)
    conn.commit()
    conn.close()
    return res


def get_or_create_duel_user_by_username(username: str, user_id: int = None) -> dict:
    """Получает или создает профиль игрока по username."""
    clean_username = _clean_name(username)
    existing = get_duel_user_by_username(clean_username)
    if existing:
        return existing

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today_str = _get_today_date_str()
    assigned_user_id = user_id or random.randint(1000000000, 9999999999)

    cursor.execute("""
        INSERT INTO duel_users (user_id, username, display_name, points, wins, losses, stolen_dicks_count, dick_stolen_count, dick_stolen_today, last_activity_date, last_stolen_by)
        VALUES (?, ?, ?, 20, 0, 0, 0, 0, 0, ?, NULL)
    """, (assigned_user_id, clean_username, clean_username, today_str))

    conn.commit()
    conn.close()

    return {
        "user_id": assigned_user_id,
        "username": clean_username,
        "display_name": clean_username,
        "points": 20,
        "wins": 0,
        "losses": 0,
        "stolen_dicks_count": 0,
        "dick_stolen_count": 0,
        "dick_stolen_today": False,
        "last_activity_date": today_str,
        "last_stolen_by": None
    }


def delete_duel_user_by_username(username: str) -> bool:
    """Удаляет дуэлянта из таблицы по username."""
    clean_username = _clean_name(username)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM duel_users WHERE LOWER(username) = LOWER(?)", (clean_username,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def execute_duel_transaction(chat_id: int, winner_user: dict, loser_user: dict, is_dick_stolen: bool):
    """Атомарная транзакция проведения дуэли."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        winner_points = min(100, winner_user["points"] + 10)
        loser_points = max(0, loser_user["points"] - 5)

        winner_name = _clean_name(winner_user.get('username') or winner_user.get('display_name', 'Кто-то'))

        if is_dick_stolen:
            cursor.execute("""
                UPDATE duel_users
                SET points = ?, wins = wins + 1, stolen_dicks_count = stolen_dicks_count + 1
                WHERE user_id = ?
            """, (winner_points, winner_user["user_id"]))

            cursor.execute("""
                UPDATE duel_users
                SET points = ?, losses = losses + 1, dick_stolen_count = dick_stolen_count + 1,
                    dick_stolen_today = 1, last_stolen_by = ?
                WHERE user_id = ?
            """, (loser_points, winner_name, loser_user["user_id"]))
        else:
            cursor.execute("""
                UPDATE duel_users
                SET points = ?, wins = wins + 1
                WHERE user_id = ?
            """, (winner_points, winner_user["user_id"]))

            cursor.execute("""
                UPDATE duel_users
                SET points = ?, losses = losses + 1
                WHERE user_id = ?
            """, (loser_points, loser_user["user_id"]))

        conn.commit()
        return winner_points, loser_points
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_duel_top(sort_by: str = "wins", limit: int = 10) -> list:
    """Топ игроков по победам или очкам."""
    valid_cols = {"wins": "wins", "points": "points"}
    sort_column = valid_cols.get(sort_by, "wins")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT username, display_name, wins, losses, points
        FROM duel_users
        ORDER BY {sort_column} DESC, wins DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ==========================================
# 📌 ОРИГИНАЛЬНЫЕ ФУНКЦИИ БОТА
# ==========================================

def save_or_update_user(user, chat_id: int):
    if user.is_bot:
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    clean_username = _clean_name(user.username or user.first_name)
    cursor.execute("""
        INSERT INTO users (user_id, chat_id, username, first_name, beauty_count, is_bot)
        VALUES (?, ?, ?, ?, 0, 0)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
    """, (user.id, chat_id, clean_username, user.first_name))
    conn.commit()
    conn.close()


def save_custom_birthdate(chat_id: int, username: str, bday_str: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    clean_username = _clean_name(username)
    cursor.execute("""
        UPDATE users 
        SET birthdate = ? 
        WHERE chat_id = ? AND LOWER(username) = LOWER(?)
    """, (bday_str, chat_id, clean_username))
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
    """Единственное место, где используется кликабельный тег @username для анонса победы."""
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

    raw_username = _clean_name(username)
    formatted_winner = f"@{raw_username}" if raw_username else "Кто-то"
    return formatted_winner, new_count


def get_top_beauties(chat_id: int, limit: int = 3):
    """Топ пидоров дня без тегов и без знака @."""
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
    return [(_clean_name(u), c) for u, c in top_users]


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