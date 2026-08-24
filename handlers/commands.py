from telegram import Update
from telegram.ext import ContextTypes
from database import get_top_beauties, pick_beauty_of_the_day, save_or_update_user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if not update.message or not update.message.from_user:
        return

    # Сохраняем/обновляем пользователя в базе данных
    save_or_update_user(update.message.from_user, update.message.chat_id)

    # Приветственное сообщение
    await update.message.reply_text("Свобода. Равенство. Пошёл нахуй.")


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /top — статистика пидоров дня (без тегов и символа @)"""
    if not update.message:
        return

    chat_id = update.message.chat_id
    top_list = get_top_beauties(chat_id, limit=10)

    if not top_list:
        await update.message.reply_text("В этом чате пока нет участников или никто ещё не побеждал.")
        return

    text = "🏆 <b>Топ пидоров чата:</b>\n\n"
    for idx, (username, count) in enumerate(top_list, 1):
        # Отображается просто как текст в тегах <b>, без @ и без пуш-уведомлений
        text += f"{idx}. <b>{username}</b> — {count} раз(а)\n"

    await update.message.reply_text(text, parse_mode="HTML")


async def force_pidor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручной запуск выбора пидора дня"""
    if not update.message:
        return

    chat_id = update.message.chat_id
    result = pick_beauty_of_the_day(chat_id)

    if not result:
        await update.message.reply_text("Нет кандидатов для проведения игры.")
        return

    winner_tag, count = result
    # Единственное место с явным кликабельным тегом @username
    await update.message.reply_text(
        f"Пидор дня — {winner_tag}! Он был пидором уже {count} раз(а)."
    )