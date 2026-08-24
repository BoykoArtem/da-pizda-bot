import random
from telegram import Update
from telegram.ext import ContextTypes
from config import DICK_STEAL_CHANCE, TOP_SORT_BY
from database import (
    get_or_create_duel_user, 
    get_duel_user_by_username, 
    execute_duel_transaction,
    get_duel_top
)

async def duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /duel @username"""
    if not update.message or not update.message.from_user or not update.message.chat:
        return

    initiator_tg = update.message.from_user

    if not context.args:
        await update.message.reply_text("🗡️ Укажите соперника: <code>/duel @username</code>", parse_mode="HTML")
        return

    target_raw = context.args[0].strip()
    target_username = target_raw.lstrip("@")

    # Проверка вызова самого себя
    if initiator_tg.username and initiator_tg.username.lower() == target_username.lower():
        await update.message.reply_text("⚔️ Нельзя вызвать на дуэль самого себя!")
        return

    # 1. Загрузка и проверка инициатора
    # Передаем None в качестве conn, так как get_or_create_duel_user сама управляет соединением
    import sqlite3
    from database import DB_NAME
    
    conn = sqlite3.connect(DB_NAME)
    try:
        initiator = get_or_create_duel_user(conn, initiator_tg)
    finally:
        conn.close()

    if initiator["dick_stolen_today"]:
        await update.message.reply_text(f"💀 @{initiator['username'] or initiator['display_name']} сегодня уже без хуя. До завтра драться нельзя.")
        return

    if initiator["points"] <= 0:
        await update.message.reply_text("⚔️ У вас 0 очков. Вы больше не можете драться сегодня.")
        return

    # 2. Загрузка и проверка противника
    opponent = get_duel_user_by_username(target_username)
    if not opponent:
        await update.message.reply_text(f"❌ Игрок @{target_username} не найден или ещё ни разу не играл.")
        return

    if opponent["dick_stolen_today"]:
        await update.message.reply_text(f"💀 @{opponent['username'] or opponent['display_name']} сегодня уже без хуя. До завтра драться нельзя.")
        return

    if opponent["points"] <= 0:
        await update.message.reply_text(f"⚔️ @{opponent['username'] or opponent['display_name']} больше не может драться сегодня — у него 0 очков.")
        return

    # 3. Расчёт шансов на основе очков
    total_points = initiator["points"] + opponent["points"]
    
    if total_points > 0:
        initiator_win_chance = initiator["points"] / total_points
    else:
        initiator_win_chance = 0.5  # Защита от деления на 0

    if random.random() < initiator_win_chance:
        winner, loser = initiator, opponent
    else:
        winner, loser = opponent, initiator

    is_dick_stolen = random.random() < DICK_STEAL_CHANCE

    # 4. Атомарное сохранение результатов
    try:
        w_after, l_after = execute_duel_transaction(
            chat_id=update.message.chat_id,
            winner_user=winner,
            loser_user=loser,
            is_dick_stolen=is_dick_stolen
        )
    except Exception:
        await update.message.reply_text("⚠️ Ошибка проведения дуэли. Попробуйте снова.")
        return

    # 5. Формирование ответа
    win_name = f"@{winner['username']}" if winner['username'] else winner['display_name']
    lose_name = f"@{loser['username']}" if loser['username'] else loser['display_name']

    res_msg = (
        f"🗡️ <b>Гномья дуэль на ножах!</b>\n\n"
        f"Победитель: <b>{win_name}</b>\n"
        f"Проигравший: <b>{lose_name}</b>\n\n"
        f"<b>{win_name}</b>: +10 очков ({w_after}/100)\n"
        f"<b>{lose_name}</b>: -5 очков ({l_after}/100)\n"
    )

    if is_dick_stolen:
        res_msg += f"\n💀 <b>И ВДОБАВОК У НЕГО УКРАЛИ ХУЙ.</b>\nСегодня {lose_name} больше не может драться."

    await update.message.reply_text(res_msg, parse_mode="HTML")


async def duel_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /duel_stats или /stats [@username]"""
    if not update.message or not update.message.from_user:
        return

    if context.args:
        target_username = context.args[0].lstrip("@")
        user_data = get_duel_user_by_username(target_username)
        if not user_data:
            await update.message.reply_text(f"❌ Пользователь @{target_username} не найден в статистике дуэлей.")
            return
    else:
        import sqlite3
        from database import DB_NAME
        
        conn = sqlite3.connect(DB_NAME)
        try:
            user_data = get_or_create_duel_user(conn, update.message.from_user)
        finally:
            conn.close()

    name = f"@{user_data['username']}" if user_data['username'] else user_data['display_name']
    stolen_status = "\n⚠️ <i>(Сегодня хуй украден)</i>" if user_data['dick_stolen_today'] else ""

    text = (
        f"🗡️ <b>Гномья дуэль на ножах</b>\n\n"
        f"👤 <b>{name}</b>{stolen_status}\n\n"
        f"Очки сегодня: <b>{user_data['points']} / 100</b>\n\n"
        f"Победы: <b>{user_data['wins']}</b>\n"
        f"Поражения: <b>{user_data['losses']}</b>\n\n"
        f"Хуй украли: <b>{user_data['dick_stolen_count']} раз</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def duel_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /duel_top"""
    top_list = get_duel_top(sort_by=TOP_SORT_BY, limit=10)
    if not top_list:
        await update.message.reply_text("🏆 Список лидеров дуэлей пока пуст.")
        return

    text = "🏆 <b>Гномья дуэль на ножах — топ игроков</b>\n\n"
    for idx, row in enumerate(top_list, 1):
        username, display_name, wins, losses, points = row
        name = f"@{username}" if username else display_name
        text += f"{idx}. <b>{name}</b> — {wins} побед ({losses} пораж., {points} очков)\n"

    await update.message.reply_text(text, parse_mode="HTML")