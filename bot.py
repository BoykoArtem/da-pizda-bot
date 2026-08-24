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

from config import BOT_TOKEN, GAME_HOUR, GAME_MINUTE, DUEL_TIMEZONE
from database import init_db
from handlers.commands import start_command, top_command, force_pidor_command
from handlers.game import daily_beauty_job
from handlers.past_pizda import schedule_past_pizda_job
from handlers.triggers import respond_trigger
from handlers.utils import get_file_id_handler, error_handler
from handlers.weather import weather_command

# Импорт хендлеров дуэлей
from handlers.duel import (
    duel_command,
    duel_stats_command,
    duel_top_command,
    duel_delete_command,
)

nest_asyncio.apply()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main():
    init_db()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Запуск планировщика
    tz = pytz.timezone(DUEL_TIMEZONE)
    target_time = time(hour=GAME_HOUR, minute=GAME_MINUTE, second=0, tzinfo=tz)

    if application.job_queue:
        application.job_queue.run_daily(daily_beauty_job, time=target_time)
        schedule_past_pizda_job(application.job_queue)

    # Регистрация стандартных команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("force_pidor", force_pidor_command))
    application.add_handler(CommandHandler("weather", weather_command))

    # Регистрация команд дуэлей (убран лишний синоним /stats)
    application.add_handler(CommandHandler("duel", duel_command))
    application.add_handler(CommandHandler("duel_stats", duel_stats_command))
    application.add_handler(CommandHandler("duel_top", duel_top_command))
    application.add_handler(CommandHandler("duel_delete", duel_delete_command))

    # Служебные хендлеры и текстовые триггеры
    media_filter = (filters.PHOTO | filters.ANIMATION | filters.VIDEO | filters.Document.ALL) & filters.ChatType.PRIVATE
    application.add_handler(MessageHandler(media_filter, get_file_id_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, respond_trigger))

    # Логгер ошибок
    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == "__main__":
    main()