import asyncio
from telegram.ext import ContextTypes
from database import pick_beauty_of_the_day, get_all_chats

def get_plural_raz(count: int) -> str:
    last_two = count % 100
    last_one = count % 10
    if 11 <= last_two <= 19:
        return "раз"
    if last_one in [2, 3, 4]:
        return "раза"
    return "раз"

async def run_pidor_game_in_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    result = pick_beauty_of_the_day(chat_id)
    if result:
        username, count = result
        word = get_plural_raz(count)
        await context.bot.send_message(chat_id=chat_id, text="Выбираем пидора дня...")
        await asyncio.sleep(3)  
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Пидор дня — {username}. Он был пидором {count} {word}."
        )
    else:
        await context.bot.send_message(chat_id=chat_id, text="В этом чате пока нет зарегистрированных участников!")

async def daily_beauty_job(context: ContextTypes.DEFAULT_TYPE):
    chats = get_all_chats()
    for (chat_id,) in chats:
        await run_pidor_game_in_chat(context, chat_id)