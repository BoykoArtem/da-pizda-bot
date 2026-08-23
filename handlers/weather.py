import random
import requests
from telegram import Update
from telegram.ext import ContextTypes
from config import GIF_FILE_ID, RUSSIA_GIF_FILE_ID, PERM_PHOTO_IDS

WEATHER_CODES = {
    0: ("☀️", "Ясно"),
    1: ("🌤️", "Преимущественно ясно"),
    2: ("⛅", "Переменная облачность"),
    3: ("☁️", "Пасмурно"),
    45: ("🌫️", "Туман"),
    48: ("🌫️", "Оседающий туман"),
    51: ("🌧️", "Лёгкая морось"),
    53: ("🌧️", "Морось"),
    55: ("🌧️", "Плотная морось"),
    61: ("☔", "Слабый дождь"),
    63: ("☔", "Умеренный дождь"),
    65: ("🌧️", "Сильный дождь"),
    71: ("❄️", "Слабый снег"),
    73: ("❄️", "Снегопад"),
    75: ("❄️", "Сильный снегопад"),
    80: ("🌦️", "Ливень"),
    95: ("⛈️", "Гроза"),
}

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weather <город> — показывает погоду или пасхалку."""
    if not update.message:
        return

    city = " ".join(context.args) if context.args else "Санкт-Петербург"
    city_normalized = city.strip().lower()

    # Пасхалка на Орёл
    if city_normalized in ["орел", "орёл"]:
        await update.message.reply_animation(animation=GIF_FILE_ID)
        return

    # Пасхалка на Россию
    if city_normalized == "россия":
        await update.message.reply_animation(animation=RUSSIA_GIF_FILE_ID)
        return

    try:
        # 1. Поиск координат через Geocoding API
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ru"
        geo_res = requests.get(geo_url, timeout=5).json()

        if not geo_res.get("results"):
            await update.message.reply_text(f"❌ Город '{city}' не найден.")
            return

        location = geo_res["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        city_name = location.get("name", city)
        country = location.get("country", "")

        # 2. Запрос погодных данных (ветер в м/с)
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current_weather=true&"
            f"hourly=relativehumidity_2m,apparent_temperature&"
            f"windspeed_unit=ms&timezone=auto"
        )
        w_res = requests.get(weather_url, timeout=5).json()
        current = w_res.get("current_weather", {})

        temp = round(current.get("temperature", 0))
        wind_speed = round(current.get("windspeed", 0))
        code = current.get("weathercode", 0)

        emoji, desc = WEATHER_CODES.get(code, ("🌡️", "Неизвестно"))
        apparent = round(w_res.get("hourly", {}).get("apparent_temperature", [temp])[0])

        message = (
            f"<b>Погода в {city_name}</b> {country}\n\n"
            f"{emoji} <b>{desc}</b>\n"
            f"🌡️ Температура: <b>{temp}°C</b> (ощущается как {apparent}°C)\n"
            f"💨 Ветер: <b>{wind_speed} м/с</b>\n"
        )

        await update.message.reply_text(message, parse_mode="HTML")

        # Дополнительная пасхалка на Пермь: отправка рандомного фото
        if city_normalized == "пермь" and PERM_PHOTO_IDS:
            random_photo_id = random.choice(PERM_PHOTO_IDS)
            await update.message.reply_photo(photo=random_photo_id)

    except Exception:
        await update.message.reply_text("⚠️ Не удалось получить данные о погоде.")