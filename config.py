import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Список ID администраторов (преобразован в set для O(1) поиска)
raw_admin_ids = os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", ""))
ADMIN_IDS = {int(x.strip()) for x in raw_admin_ids.split(",") if x.strip().isdigit()}

# --- GIF и Медиа файлы ---
GIF_FILE_ID = "CgACAgIAAx0CT5HpJwABIvLFaom6NKy2zmkAAWBNrsYmFfgTcoB7AAJxJQAC81hYSW_i-PO0dPOWPQQ"
BIRTHDAY_GIF_ID = "CgACAgQAAxkBAAIFBGqJwbeWNNoHZyHu6jPdOEK2DDa9AAIjAwAC0DoFU1R2_ufiAzEAAT0E"
RUSSIA_GIF_FILE_ID = "CgACAgIAAxkBAAIFemqLJ9bNTsg1KqypNQFdHi7zJY3YAAK0NgACGLQ4StOiwaNwIPsPPQQ"
WINNER_100_PTS_GIF = "CgACAgIAAx0CT5HpJwABIvnBao1gIevcBSmVkSVPoihctaZDNDMAAuiEAAJdEHFIpAui-RjE9Ek9BA"

LET_DO_STICKER_IDS = [
    "CAACAgIAAxkBAAERxb1qiy1ELop7BAbp2OuaV5odzQibBwACQxsAAgGEKUuE9pPRkzKm0j0E",
    "CAACAgIAAxkBAAERxb9qiy1NuEpe_5ycltOj-JxAplvA4gAC0RcAAtk5KUslsIBH-f94pD0E",
]

PERM_PHOTO_IDS = [
    "AgACAgIAAxkBAAIFfmqLK9APwKZ2VzzlTMUE9AE4vNadAALwIGsbTjJYSO5CxBV7789fAQADAgADeAADPQQ",
    "AgACAgIAAxkBAAIFf2qLK97PVxvwbDQa-2_1pRSA2mYpAALxIGsbTjJYSPNL5z3lbLgAAQEAAwIAA3gAAz0E",
    "AgACAgIAAxkBAAIFgGqLLAUxeNWrFWZNEF7eoDz6CtuuAALyIGsbTjJYSHH4ClLDZaxHAQADAgADeAADPQQ",
    "AgACAgIAAxkBAAIFgWqLLA7BlSd3xnhpC32hIfHBo4-uAALzIGsbTjJYSHGh9N8_CQzPAQADAgADeAADPQQ",
    "AgACAgIAAxkBAAIFgmqLLCVkVe49zX1OsI9qe96mM3t2AAL2IGsbTjJYSBSNvamUAx2HAQADAgADeAADPQQ",
    "AgACAgIAAxkBAAIFg2qLLLcaU9iagtLlp6rfqd7_-hEMAAL3IGsbTjJYSOrHN3s5l_TrAQADAgADeAADPQQ",
]

# --- Настройки планировщика ---
GAME_HOUR = 18
GAME_MINUTE = 0
DUEL_TIMEZONE = "Europe/Moscow"

# --- Настройки Гномьей дуэли ---
DAILY_START_POINTS = 20
MAX_DAILY_POINTS = 100
WIN_POINTS = 10
LOSS_POINTS = 5
DICK_STEAL_CHANCE = 0.20  # 20%
DUEL_WIN_CHANCE = 0.50    # 50%
TOP_SORT_BY = "wins"      # "wins" | "net_wins" | "points"