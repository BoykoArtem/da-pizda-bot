import html
import random
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes
from config import DICK_STEAL_CHANCE, TOP_SORT_BY, ADMIN_IDS
from database import (
    DB_NAME,
    get_or_create_duel_user,
    get_duel_user_by_username,
    delete_duel_user_by_username,
    execute_duel_transaction,
    get_duel_top,
)

AUTO_DELETE_DELAY = 60


async def delete_messages_job(context: ContextTypes.DEFAULT_TYPE):
    """Удаляет исходную команду и ответ бота."""
    job_data = context.job.data
    chat_id = job_data.get("chat_id")
    message_ids = job_data.get("message_ids", [])

    for msg_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass


def schedule_auto_delete(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list[int]
):
    """Планирует удаление сообщений через 60 секунд."""
    if context.job_queue:
        context.job_queue.run_once(
            delete_messages_job,
            when=AUTO_DELETE_DELAY,
            data={"chat_id": chat_id, "message_ids": message_ids},
        )


def _extract_username(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str | None:
    """Извлекает юзернейм/имя без знака @."""
    if context.args:
        return context.args[0].strip().lstrip("@")

    msg_text = update.message.text or ""
    parts = msg_text.split()
    if len(parts) > 1:
        return parts[1].strip().lstrip("@")

    return None


def _get_safe_name(user_dict: dict) -> str:
    """Безопасно возвращает экранированное имя для HTML."""
    raw_name = (
        user_dict.get("username") or user_dict.get("display_name") or "Игрок"
    )
    return html.escape(str(raw_name))


async def send_and_schedule(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    parse_mode: str = "HTML",
):
    """Отправляет ответ бота и ставит удаление в очередь."""
    bot_msg = await update.message.reply_text(text, parse_mode=parse_mode)
    schedule_auto_delete(
        context,
        chat_id=update.message.chat_id,
        message_ids=[update.message.message_id, bot_msg.message_id],
    )


async def duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /duel [username]"""
    if not update.message or not update.message.from_user or not update.message.chat:
        return

    chat_id = update.message.chat_id
    initiator_tg = update.message.from_user
    target_username = _extract_username(update, context)

    if not target_username:
        await send_and_schedule(
            update,
            context,
            "🗡️ Укажите соперника без собаки: <code>/duel username</code>",
        )
        return

    # Проверка самовызова
    if (
        initiator_tg.username
        and initiator_tg.username.lower() == target_username.lower()
    ):
        await send_and_schedule(
            update, context, "⚔️ Нельзя вызвать на дуэль самого себя!"
        )
        return

    conn = sqlite3.connect(DB_NAME)
    try:
        initiator = get_or_create_duel_user(conn, initiator_tg, chat_id)
    finally:
        conn.close()

    init_name = _get_safe_name(initiator)

    if initiator["dick_stolen_today"]:
        await send_and_schedule(
            update,
            context,
            f"💀 <b>{init_name}</b> сегодня уже без хуя. До завтра драться нельзя.",
        )
        return

    if initiator["points"] <= 0:
        await send_and_schedule(
            update,
            context,
            "⚔️ У вас 0 очков. Вы больше не можете драться сегодня.",
        )
        return

    # 1. Сначала ищем в базе данных
    conn = sqlite3.connect(DB_NAME)
    try:
        opponent = get_duel_user_by_username(conn, target_username, chat_id)
    finally:
        conn.close()

    # 2. Если в базе нет — проверяем присутствие в чате через API Telegram
    if not opponent:
        try:
            chat_member = await context.bot.get_chat_member(chat_id, f"@{target_username}")
            if chat_member and chat_member.user:
                conn = sqlite3.connect(DB_NAME)
                try:
                    opponent = get_or_create_duel_user(conn, chat_member.user, chat_id)
                finally:
                    conn.close()
        except Exception:
            opponent = None

    if not opponent:
        safe_target = html.escape(target_username)
        await send_and_schedule(
            update,
            context,
            f"❌ Соперник <b>{safe_target}</b> не найден в этом чате.",
        )
        return

    opp_name = _get_safe_name(opponent)

    if opponent["dick_stolen_today"]:
        await send_and_schedule(
            update,
            context,
            f"💀 <b>{opp_name}</b> сегодня уже без хуя. До завтра драться нельзя.",
        )
        return

    if opponent["points"] <= 0:
        await send_and_schedule(
            update,
            context,
            f"⚔️ <b>{opp_name}</b> больше не может драться сегодня — у него 0 очков.",
        )
        return

    total_points = initiator["points"] + opponent["points"]
    initiator_win_chance = (
        initiator["points"] / total_points if total_points > 0 else 0.5
    )

    if random.random() < initiator_win_chance:
        winner, loser = initiator, opponent
    else:
        winner, loser = opponent, initiator

    is_dick_stolen = random.random() < DICK_STEAL_CHANCE

    try:
        w_after, l_after = execute_duel_transaction(
            chat_id=chat_id,
            winner_user=winner,
            loser_user=loser,
            is_dick_stolen=is_dick_stolen,
        )
    except Exception:
        await send_and_schedule(
            update, context, "⚠️ Ошибка проведения дуэли. Попробуйте снова."
        )
        return

    win_name = _get_safe_name(winner)
    lose_name = _get_safe_name(loser)

    res_msg = (
        f"🗡️ <b>Гномья дуэль на ножах!</b>\n\n"
        f"Победитель: <b>{win_name}</b>\n"
        f"Проигравший: <b>{lose_name}</b>\n\n"
        f"<b>{win_name}</b>: +10 очков ({w_after}/100)\n"
        f"<b>{lose_name}</b>: -5 очков ({l_after}/100)\n"
    )

    if is_dick_stolen:
        res_msg += (
            f"\n💀 <b>И ВДОБАВОК У НЕГО УКРАЛИ ХУЙ.</b>\n"
            f"Сегодня {lose_name} больше не может драться."
        )

    await send_and_schedule(update, context, res_msg)


async def duel_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /duel_stats [username]"""
    if not update.message or not update.message.from_user or not update.message.chat:
        return

    chat_id = update.message.chat_id
    target_username = _extract_username(update, context)

    if target_username:
        conn = sqlite3.connect(DB_NAME)
        try:
            user_data = get_duel_user_by_username(conn, target_username, chat_id)
        finally:
            conn.close()

        if not user_data:
            try:
                chat_member = await context.bot.get_chat_member(chat_id, f"@{target_username}")
                if chat_member and chat_member.user:
                    conn = sqlite3.connect(DB_NAME)
                    try:
                        user_data = get_or_create_duel_user(conn, chat_member.user, chat_id)
                    finally:
                        conn.close()
            except Exception:
                user_data = None

        if not user_data:
            safe_target = html.escape(target_username)
            await send_and_schedule(
                update,
                context,
                f"❌ Пользователь <b>{safe_target}</b> не найден в статистике этого чата.",
            )
            return
    else:
        conn = sqlite3.connect(DB_NAME)
        try:
            user_data = get_or_create_duel_user(
                conn, update.message.from_user, chat_id
            )
        finally:
            conn.close()

    name = _get_safe_name(user_data)

    stolen_status = ""
    if user_data["dick_stolen_today"]:
        thief = user_data.get("last_stolen_by")
        if thief:
            stolen_status = (
                f"\n⚠️ <i>(Сегодня хуй украл {html.escape(str(thief))})</i>"
            )
        else:
            stolen_status = "\n⚠️ <i>(Сегодня хуй украден)</i>"

    text = (
        f"🗡️ <b>Гномья дуэль на ножах</b>\n\n"
        f"👤 <b>{name}</b>{stolen_status}\n\n"
        f"Очки сегодня: <b>{user_data['points']} / 100</b>\n\n"
        f"Победы: <b>{user_data['wins']}</b>\n"
        f"Поражения: <b>{user_data['losses']}</b>\n\n"
        f"💄 Украл хуев: <b>{user_data.get('stolen_dicks_count', 0)}</b>\n"
        f"💄 Хуй украли: <b>{user_data['dick_stolen_count']} раз</b>"
    )
    await send_and_schedule(update, context, text)


async def duel_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /duel_top"""
    if not update.message or not update.message.chat:
        return

    chat_id = update.message.chat_id

    conn = sqlite3.connect(DB_NAME)
    try:
        top_list = get_duel_top(conn, chat_id, 10, TOP_SORT_BY)
    finally:
        conn.close()

    if not top_list:
        await send_and_schedule(
            update, context, "🏆 Список лидеров дуэлей в этом чате пока пуст."
        )
        return

    text = "🏆 <b>Гномья дуэль на ножах — топ игроков</b>\n\n"
    for idx, row in enumerate(top_list, 1):
        username, display_name, wins, losses, points = row
        name = html.escape(str(username or display_name or "Игрок"))
        text += f"{idx}. <b>{name}</b> — {wins} побед ({losses} пораж., {points} очков)\n"

    await send_and_schedule(update, context, text)


async def duel_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админское удаление игрока из дуэльной базы текущего чата: /duel_delete [username]"""
    if not update.message or not update.message.from_user or not update.message.chat:
        return

    if update.message.from_user.id not in ADMIN_IDS:
        await send_and_schedule(
            update, context, "⛔ Эта команда доступна только администраторам бота."
        )
        return

    chat_id = update.message.chat_id
    target_username = _extract_username(update, context)

    if not target_username:
        await send_and_schedule(
            update,
            context,
            "🗑️ Укажите ник без собаки: <code>/duel_delete username</code>",
        )
        return

    conn = sqlite3.connect(DB_NAME)
    try:
        deleted = delete_duel_user_by_username(conn, target_username, chat_id)
    finally:
        conn.close()

    safe_target = html.escape(target_username)

    if deleted:
        await send_and_schedule(
            update,
            context,
            f"✅ Пользователь <b>{safe_target}</b> удалён из дуэльной базы этого чата.",
        )
    else:
        await send_and_schedule(
            update,
            context,
            f"❌ Пользователь <b>{safe_target}</b> не найден в БД этого чата.",
        )