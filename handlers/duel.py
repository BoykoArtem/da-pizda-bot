import json
import random
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import DICK_STEAL_CHANCE, TOP_SORT_BY, ADMIN_IDS
from database import (
    get_or_create_duel_user,
    get_duel_user_by_username,
    delete_duel_user_by_username,
    execute_duel_transaction,
    get_duel_top,
    format_user_title
)

AUTO_DELETE_DELAY = 60

_DWARFS_FACTS_PATH = Path(__file__).resolve().parent.parent / "data" / "dwarfs_facts.json"
with open(_DWARFS_FACTS_PATH, encoding="utf-8") as _facts_file:
    DWARFS_FACTS = tuple(json.load(_facts_file)["facts"])


async def delete_messages_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data.get("chat_id")
    message_ids = job_data.get("message_ids", [])

    for msg_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass


def schedule_auto_delete(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list[int]):
    if context.job_queue:
        context.job_queue.run_once(
            delete_messages_job,
            when=AUTO_DELETE_DELAY,
            data={"chat_id": chat_id, "message_ids": message_ids}
        )


def _extract_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    if context.args:
        return context.args[0].strip().lstrip("@")

    if update.message and update.message.text:
        parts = update.message.text.split()
        if len(parts) > 1:
            return parts[1].strip().lstrip("@")

    return None


async def send_and_schedule(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup = None,
    parse_mode: str = "HTML"
):
    chat_id = update.effective_chat.id
    msg_id_to_delete = update.message.message_id if update.message else None

    try:
        if update.message:
            bot_msg = await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            bot_msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception:
        bot_msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, reply_markup=reply_markup)

    to_delete = [bot_msg.message_id]
    if msg_id_to_delete:
        to_delete.append(msg_id_to_delete)

    schedule_auto_delete(context, chat_id=chat_id, message_ids=to_delete)


async def _process_duel_fight(
    context: ContextTypes.DEFAULT_TYPE,
    initiator_tg,
    target_username: str,
    chat_id: int,
    original_msg_id: int = None
):
    if initiator_tg.username and initiator_tg.username.lower() == target_username.lower():
        bot_msg = await context.bot.send_message(chat_id, "⚔️ Нельзя вызвать на дуэль самого себя!")
        schedule_auto_delete(context, chat_id, [bot_msg.message_id])
        return

    initiator = get_or_create_duel_user(initiator_tg, chat_id)
    init_title = format_user_title(initiator)

    if initiator["dick_stolen_today"]:
        bot_msg = await context.bot.send_message(chat_id, f"💀 <b>{init_title}</b> сегодня уже без хуя. До завтра драться нельзя.", parse_mode="HTML")
        schedule_auto_delete(context, chat_id, [bot_msg.message_id])
        return

    if initiator["points"] <= 0:
        bot_msg = await context.bot.send_message(chat_id, "⚔️ У вас 0 очков. Вы больше не можете драться сегодня.")
        schedule_auto_delete(context, chat_id, [bot_msg.message_id])
        return

    opponent = get_duel_user_by_username(target_username, chat_id)
    if not opponent:
        bot_msg = await context.bot.send_message(chat_id, f"❌ Пользователь <b>{target_username}</b> не найден в базе этого чата.", parse_mode="HTML")
        schedule_auto_delete(context, chat_id, [bot_msg.message_id])
        return

    if opponent["user_id"] == initiator["user_id"]:
        bot_msg = await context.bot.send_message(chat_id, "⚔️ Нельзя вызвать на дуэль самого себя!")
        schedule_auto_delete(context, chat_id, [bot_msg.message_id])
        return

    opp_title = format_user_title(opponent)

    if opponent["dick_stolen_today"]:
        bot_msg = await context.bot.send_message(chat_id, f"💀 <b>{opp_title}</b> сегодня уже без хуя. До завтра драться нельзя.", parse_mode="HTML")
        schedule_auto_delete(context, chat_id, [bot_msg.message_id])
        return

    if opponent["points"] <= 0:
        bot_msg = await context.bot.send_message(chat_id, f"⚔️ <b>{opp_title}</b> больше не может драться сегодня — у него 0 очков.", parse_mode="HTML")
        schedule_auto_delete(context, chat_id, [bot_msg.message_id])
        return

    total_points = initiator["points"] + opponent["points"]
    initiator_win_chance = initiator["points"] / total_points if total_points > 0 else 0.5

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
            is_dick_stolen=is_dick_stolen
        )
    except Exception:
        bot_msg = await context.bot.send_message(chat_id, "⚠️ Ошибка проведения дуэли. Попробуйте снова.")
        schedule_auto_delete(context, chat_id, [bot_msg.message_id])
        return

    win_title = format_user_title(winner)
    lose_title = format_user_title(loser)

    res_msg = (
        f"🗡️ <b>Гномья дуэль на ножах!</b>\n\n"
        f"Победитель: <b>{win_title}</b>\n"
        f"Проигравший: <b>{lose_title}</b>\n\n"
        f"<b>{win_title}</b>: +10 очков ({w_after}/100)\n"
        f"<b>{lose_title}</b>: -5 очков ({l_after}/100)\n"
    )

    if is_dick_stolen:
        fact = random.choice(DWARFS_FACTS)
        res_msg += (
            f"\n💀 <b>И ВДОБАВОК У НЕГО УКРАЛИ ХУЙ.</b>\n"
            f"Сегодня {lose_title} больше не может драться.\n\n"
            f"📖 <i>{fact}</i>"
        )

    bot_msg = await context.bot.send_message(chat_id, res_msg, parse_mode="HTML")

    to_delete = []
    if not is_dick_stolen:
        to_delete.append(bot_msg.message_id)
    if original_msg_id:
        to_delete.append(original_msg_id)

    if to_delete:
        schedule_auto_delete(context, chat_id, to_delete)


async def duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user or not update.message.chat:
        return

    chat_id = update.message.chat_id
    initiator_tg = update.message.from_user
    target_username = _extract_username(update, context)

    if not target_username:
        top_list = get_duel_top(chat_id=chat_id, limit=20)
        keyboard = []
        for row in top_list:
            username, display_name, _, _, _ = row

            if not username:
                continue

            if initiator_tg.username and initiator_tg.username.lower() == username.lower():
                continue

            opponent = get_duel_user_by_username(username, chat_id)
            if not opponent:
                continue

            if opponent["points"] <= 0 or opponent["dick_stolen_today"]:
                continue

            clean_label = (display_name or username).lstrip("@")
            label = f"⚔️ {clean_label}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"start_duel_{username}")])

        if not keyboard:
            await send_and_schedule(update, context, "❌ В чате нет доступных соперников для дуэли (все без очков или без хуев).")
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_and_schedule(update, context, "🗡️ <b>Выберите соперника для дуэли:</b>", reply_markup=reply_markup)
        return

    await _process_duel_fight(context, initiator_tg, target_username, chat_id, original_msg_id=update.message.message_id)


async def duel_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data or not query.data.startswith("start_duel_"):
        return

    target_username = query.data.replace("start_duel_", "")
    initiator_tg = query.from_user
    chat_id = update.effective_chat.id

    await query.answer()

    try:
        await query.message.delete()
    except Exception:
        pass

    await _process_duel_fight(context, initiator_tg, target_username, chat_id)


async def duel_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user or not update.message.chat:
        return

    chat_id = update.message.chat_id
    user = get_or_create_duel_user(update.message.from_user, chat_id)
    title = format_user_title(user)

    status = "Без хуя 💀" if user["dick_stolen_today"] else "С хуем 🍆"

    text = (
        f"📊 <b>Статистика дуэлей: {title}</b>\n\n"
        f"Очки: <b>{user['points']} / 100</b>\n"
        f"Побед: <b>{user['wins']}</b>\n"
        f"Поражений: <b>{user['losses']}</b>\n"
        f"Украдено хуев: <b>{user['stolen_dicks_count']}</b>\n"
        f"Статус на сегодня: <b>{status}</b>"
    )

    await send_and_schedule(update, context, text)


async def duel_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.chat:
        return

    chat_id = update.message.chat_id
    top = get_duel_top(chat_id=chat_id, limit=10)

    if not top:
        await send_and_schedule(update, context, "🏆 Таблица лидеров чата пока пуста.")
        return

    sort_label = "очкам" if TOP_SORT_BY == "points" else "победам"
    text = f"🏆 <b>Топ-10 гномьих дуэлянтов чата (по {sort_label}):</b>\n\n"

    for idx, row in enumerate(top, 1):
        username, display_name, wins, losses, points = row
        raw_name = display_name or username or "Гном"
        clean_name = raw_name.lstrip("@")
        text += f"{idx}. <b>{clean_name}</b> — {points} очков ({wins}W / {losses}L)\n"

    await send_and_schedule(update, context, text)


async def duel_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user or not update.message.chat:
        return

    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await send_and_schedule(update, context, "⛔ Недостаточно прав.")
        return

    target_username = _extract_username(update, context)
    if not target_username:
        await send_and_schedule(update, context, "⚠️ Укажите ник: <code>/duel_delete username</code>")
        return

    chat_id = update.message.chat_id
    deleted = delete_duel_user_by_username(target_username, chat_id)

    clean_target = target_username.lstrip("@")
    if deleted:
        await send_and_schedule(update, context, f"✅ Пользователь {clean_target} удален из базы дуэлей этого чата.")
    else:
        await send_and_schedule(update, context, f"❌ Пользователь {clean_target} не найден в базе этого чата.")