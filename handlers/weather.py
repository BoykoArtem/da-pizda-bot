import requests
from telegram import Update
from telegram.ext import ContextTypes
from config import GIF_FILE_ID

# Сопоставление кодов погоды Open-Meteo с эмодзи и описанием
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

    # Если город не указан, дефолтный — Санкт-Петербург
    city = " ".join(context.args) if context.args else "Санкт-Петербург"

    # Пасхалка на Орёл
    if city.strip().lower() in ["орел", "орёл"]:
        await update.message.reply_animation(animation=GIF_FILE_ID)
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

        # 2. Запрос текущих погодных данных
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current_weather=true&"
            f"hourly=relativehumidity_2m,apparent_temperature&timezone=auto"
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
            f"💨 Ветер: <b>{wind_speed} км/ч</b>\n"
        )

        await update.message.reply_text(message, parse_mode="HTML")

    except Exception:
        await update.message.reply_text("⚠️ Не удалось получить данные о погоде.")