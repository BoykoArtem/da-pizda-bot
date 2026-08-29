import random
import requests
from telegram import Update, ForceReply, Message
from telegram.ext import ContextTypes, filters
from config import (
    OREL_GIF_IDS,
    RUSSIA_GIF_FILE_ID,
    PERM_PHOTO_IDS,
    MOSCOW_PHOTO_IDS,
    MOSCOW_STICKER_IDS,
    SPB_PHOTO_IDS,
    NSK_PHOTO_IDS,
)

WEATHER_CITY_PROMPT = "Введите название города:"

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


class WeatherCityReplyFilter(filters.MessageFilter):
    def filter(self, message):
        reply = message.reply_to_message
        if not reply or not reply.text:
            return False
        return reply.text.startswith(WEATHER_CITY_PROMPT)


weather_city_reply_filter = WeatherCityReplyFilter()


async def _send_weather(message: Message, city: str):
    city_normalized = city.strip().lower()

    # Пасхалка на Орёл
    if city_normalized in ["орел", "орёл"] and OREL_GIF_IDS:
        await message.reply_animation(animation=random.choice(OREL_GIF_IDS))
        return

    # Пасхалка на Россию
    if city_normalized == "россия":
        await message.reply_animation(animation=RUSSIA_GIF_FILE_ID)
        return

    try:
        # 1. Поиск координат через Geocoding API
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ru"
        geo_res = requests.get(geo_url, timeout=5).json()

        if not geo_res.get("results"):
            await message.reply_text(f"❌ Город '{city}' не найден.")
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

        text = (
            f"<b>Погода в {city_name}</b> {country}\n\n"
            f"{emoji} <b>{desc}</b>\n"
            f"🌡️ Температура: <b>{temp}°C</b> (ощущается как {apparent}°C)\n"
            f"💨 Ветер: <b>{wind_speed} м/с</b>\n"
        )

        await message.reply_text(text, parse_mode="HTML")

        # Дополнительная пасхалка на Москву: рандомное фото или стикер
        if city_normalized in ("москва", "moscow"):
            moscow_media = (
                [("photo", photo_id) for photo_id in MOSCOW_PHOTO_IDS]
                + [("sticker", sticker_id) for sticker_id in MOSCOW_STICKER_IDS]
            )
            if moscow_media:
                media_type, media_id = random.choice(moscow_media)
                if media_type == "photo":
                    await message.reply_photo(photo=media_id)
                else:
                    await message.reply_sticker(sticker=media_id)

        # Дополнительная пасхалка на Питер: отправка рандомного фото
        if city_normalized in (
            "питер",
            "спб",
            "петербург",
            "санкт-петербург",
            "санкт петербург",
            "spb",
            "petersburg",
        ) and SPB_PHOTO_IDS:
            await message.reply_photo(photo=random.choice(SPB_PHOTO_IDS))

        # Дополнительная пасхалка на Новосибирск: отправка рандомного фото
        if city_normalized in ("новосибирск", "новосиб", "нск", "nsk", "novosibirsk") and NSK_PHOTO_IDS:
            await message.reply_photo(photo=random.choice(NSK_PHOTO_IDS))

        # Дополнительная пасхалка на Пермь: отправка рандомного фото
        if city_normalized == "пермь" and PERM_PHOTO_IDS:
            random_photo_id = random.choice(PERM_PHOTO_IDS)
            await message.reply_photo(photo=random_photo_id)

    except Exception:
        await message.reply_text("⚠️ Не удалось получить данные о погоде.")


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weather <город> — показывает погоду или пасхалку."""
    if not update.message:
        return

    city = " ".join(context.args).strip() if context.args else ""
    if city:
        await _send_weather(update.message, city)
        return

    await update.message.reply_text(
        WEATHER_CITY_PROMPT,
        reply_markup=ForceReply(
            selective=True,
            input_field_placeholder="Например: Москва",
        ),
    )


async def weather_city_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    city = update.message.text.strip()
    if not city:
        return

    await _send_weather(update.message, city)
