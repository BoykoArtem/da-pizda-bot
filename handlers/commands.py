from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import save_or_update_user, get_top_beauties
from handlers.game import run_pidor_game_in_chat, get_plural_raz

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        save_or_update_user(update.message.from_user, update.message.chat_id)
    await update.message.reply_text("Здарова ебать")

async def force_pidor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return
    if ADMIN_ID and update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет прав для принудительного запуска.")
        return
    await update.message.reply_text("⚡ Ручной запуск игры администратором...")
    await run_pidor_game_in_chat(context, update.message.chat_id)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.message.chat_id
    top_list = get_top_beauties(chat_id, limit=3)
    if not top_list:
        await update.message.reply_text("В этом чате ещё никто не становился пидором дня!")
        return

    medals = ["1. 🥇", "2. 🥈", "3. 🥉"]
    message_lines = ["🏆 <b>Топ-3 пидора дня за всё время:</b>\n"]
    for i, (username, count) in enumerate(top_list):
        word = get_plural_raz(count)
        message_lines.append(f"{medals[i]} {username} — {count} {word}")

    await update.message.reply_text("\n".join(message_lines), parse_mode="HTML")