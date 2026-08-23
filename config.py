import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# File ID гифок
GIF_FILE_ID = "CgACAgIAAx0CT5HpJwABIvLFaom6NKy2zmkAAWBNrsYmFfgTcoB7AAJxJQAC81hYSW_i-PO0dPOWPQQ"
BIRTHDAY_GIF_ID = "CgACAgQAAxkBAAIFBGqJwbeWNNoHZyHu6jPdOEK2DDa9AAIjAwAC0DoFU1R2_ufiAzEAAT0E"
RUSSIA_GIF_FILE_ID = "CgACAgIAAxkBAAIFemqLJ9bNTsg1KqypNQFdHi7zJY3YAAK0NgACGLQ4StOiwaNwIPsPPQQ"

# Время запуска авто-игры (МСК)
GAME_HOUR = 18
GAME_MINUTE = 0