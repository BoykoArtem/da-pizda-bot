import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID

async def get_gif_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user:
        return
    if ADMIN_ID and msg.from_user.id != ADMIN_ID:
        return

    file_id = None
    if msg.animation:
        file_id = msg.animation.file_id
    elif msg.video:
        file_id = msg.video.file_id
    elif msg.document:
        file_id = msg.document.file_id

    if file_id:
        await msg.reply_text(f"GIF file_id:\n<code>{file_id}</code>", parse_mode="HTML")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Исключение при обработке запроса:", exc_info=context.error)