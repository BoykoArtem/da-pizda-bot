import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID

async def get_file_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user:
        return
    if ADMIN_ID and msg.from_user.id != ADMIN_ID:
        return

    file_id = None
    media_type = "File"

    # 1. Сжатая картинка (Telegram отправляет массив размеров, берем самое высокое качество - последний элемент)
    if msg.photo:
        file_id = msg.photo[-1].file_id
        media_type = "Photo"

    # 2. Анимация / GIF
    elif msg.animation:
        file_id = msg.animation.file_id
        media_type = "GIF"

    # 3. Видео
    elif msg.video:
        file_id = msg.video.file_id
        media_type = "Video"

    # 4. Документ (картинка или файл, отправленный "без сжатия")
    elif msg.document:
        file_id = msg.document.file_id
        media_type = "Document"

    # 5. Стикер
    elif msg.sticker:
        file_id = msg.sticker.file_id
        media_type = "Sticker"

    if file_id:
        await msg.reply_text(f"{media_type} file_id:\n<code>{file_id}</code>", parse_mode="HTML")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Исключение при обработке запроса:", exc_info=context.error)