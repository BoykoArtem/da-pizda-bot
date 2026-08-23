import json
import re
import random
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from config import GIF_FILE_ID, BIRTHDAY_GIF_ID, LET_DO_STICKER_IDS
from database import (
    save_or_update_user,
    save_custom_birthdate,
    get_user_birthdate_from_db,
    mark_pizda_candidate_used,
)
from handlers.past_pizda import match_yes_no, remember_pizda_candidate

_LET_DO_PHRASES_PATH = Path(__file__).resolve().parent.parent / "data" / "let_do_phrases.json"
with open(_LET_DO_PHRASES_PATH, encoding="utf-8") as _phrases_file:
    LET_DO_PHRASES = tuple(json.load(_phrases_file))

async def respond_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return

    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    text_raw = (update.message.text or "").strip()

    save_or_update_user(update.message.from_user, chat_id)

    # Запись ДР по шаблону @username 26.01.1994
    bday_pattern = r"^(@\w+)\s+(\d{2}\.\d{2}(?:\.\d{4})?)$"
    match = re.match(bday_pattern, text_raw)
    if match:
        target_username, bday_str = match.groups()
        if save_custom_birthdate(chat_id, target_username, bday_str):
            await update.message.reply_text(
                f"Запомнил! День рождения для {target_username}: {bday_str}",
                reply_to_message_id=update.message.message_id
            )
        else:
            await update.message.reply_text(
                f"Пользователь {target_username} ещё не писал в этом чате, не могу сохранить дату.",
                reply_to_message_id=update.message.message_id
            )
        return

    now = datetime.now()
    last_responded = context.user_data.get(user_id)

    # Реакция на пересланные сообщения
    if update.message.forward_origin is not None and random.random() < 0.3:
        await update.message.reply_text("Форварднул тебе за щеку, проверяй", reply_to_message_id=update.message.message_id)

    # Дни рождения
    is_bday_today = False
    try:
        chat = await context.bot.get_chat(user_id)
        if hasattr(chat, 'birthdate') and chat.birthdate:
            bday = chat.birthdate
            if bday.day == now.day and bday.month == now.month:
                is_bday_today = True
    except Exception as e:
        logging.debug(f"Не удалось проверить ДР через API Telegram для {user_id}: {e}")

    if not is_bday_today:
        db_bday = get_user_birthdate_from_db(user_id, chat_id)
        if db_bday:
            try:
                parts = db_bday.split(".")
                if int(parts[0]) == now.day and int(parts[1]) == now.month:
                    is_bday_today = True
            except (ValueError, IndexError):
                pass

    if is_bday_today:
        congrat_key = f"bday_{now.year}"
        if not context.user_data.get(congrat_key):
            context.user_data[congrat_key] = True
            user_name = update.message.from_user.first_name
            text = f"🎉 С днём рождения, {user_name}! 🥳🎂"
            if BIRTHDAY_GIF_ID:
                await update.message.reply_animation(animation=BIRTHDAY_GIF_ID, caption=text)
            else:
                await update.message.reply_text(text)

    if any(phrase in text_raw.lower() for phrase in LET_DO_PHRASES) and random.random() < 0.05:
        await update.message.reply_sticker(
            sticker=random.choice(LET_DO_STICKER_IDS),
            reply_to_message_id=update.message.message_id,
        )

    yes_no = match_yes_no(text_raw)
    if yes_no == "да":
        remember_pizda_candidate(chat_id, update.message.message_id, update.message.date)

    # Ответы "Да/Нет" и троллинг Amigo
    response_chance = 0.09
    if last_responded is None or random.random() < response_chance:
        if yes_no == "да":
            await update.message.reply_text("Пизда", reply_to_message_id=update.message.message_id)
            mark_pizda_candidate_used(chat_id, update.message.message_id)
        elif yes_no == "нет":
            await update.message.reply_text("Пидора ответ", reply_to_message_id=update.message.message_id)

        user_first_name = (update.message.from_user.first_name or "").lower()
        if user_first_name == "amigo":
            if random.random() < 0.3:
                await update.message.reply_text("Может быть ты покинешь чат?", reply_to_message_id=update.message.message_id)
            if random.random() < 0.3:
                await update.message.reply_animation(animation=GIF_FILE_ID, reply_to_message_id=update.message.message_id)

        context.user_data[user_id] = now