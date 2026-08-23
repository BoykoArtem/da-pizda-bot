import logging
from datetime import time
import pytz
import nest_asyncio

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, GAME_HOUR, GAME_MINUTE
from database import init_db
from handlers.commands import start_command, top_command, force_pidor_command
from handlers.game import daily_beauty_job
from handlers.triggers import respond_trigger
from handlers.utils import get_file_id_handler, error_handler
from handlers.weather import weather_command

nest_asyncio.apply()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def main():
    init_db()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Запуск планировщика
    moscow_tz = pytz.timezone("Europe/Moscow")
    target_time = time(hour=GAME_HOUR, minute=GAME_MINUTE, second=0, tzinfo=moscow_tz)
    
    if application.job_queue:
        application.job_queue.run_daily(daily_beauty_job, time=target_time)

    # Регистрация команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("force_pidor", force_pidor_command))
    application.add_handler(CommandHandler("weather", weather_command))
    
    # Служебные хендлеры и текстовые триггеры (добавлен filters.PHOTO)
    media_filter = (filters.PHOTO | filters.ANIMATION | filters.VIDEO | filters.Document.ALL) & filters.ChatType.PRIVATE
    application.add_handler(MessageHandler(media_filter, get_file_id_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, respond_trigger))

    # Логгер ошибок
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == "__main__":
    main()