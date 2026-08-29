import random
import uuid
import requests
from telegram import (
    Update,
    InlineQueryResultArticle,
    InlineQueryResultCachedMpeg4Gif,
    InlineQueryResultCachedPhoto,
    InputTextMessageContent,
)
from telegram.ext import ContextTypes
from config import (
    OREL_GIF_IDS,
    RUSSIA_GIF_FILE_ID,
    PERM_PHOTO_IDS,
    MOSCOW_PHOTO_IDS,
    SPB_PHOTO_IDS,
    NSK_PHOTO_IDS,
)

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

SPB_ALIASES = (
    "питер",
    "спб",
    "петербург",
    "санкт-петербург",
    "санкт петербург",
    "spb",
    "petersburg",
)
NSK_ALIASES = ("новосибирск", "новосиб", "нск", "nsk", "novosibirsk")
MOSCOW_ALIASES = ("москва", "moscow", "мск", "msk")
PERM_ALIASES = ("пермь", "perm")

# Короткие названия → то, что уходит в геокодинг
CITY_GEO_QUERY = {}
for _alias in SPB_ALIASES:
    CITY_GEO_QUERY[_alias] = "Санкт-Петербург"
for _alias in MOSCOW_ALIASES:
    CITY_GEO_QUERY[_alias] = "Москва"
for _alias in NSK_ALIASES:
    CITY_GEO_QUERY[_alias] = "Новосибирск"
for _alias in PERM_ALIASES:
    CITY_GEO_QUERY[_alias] = "Пермь"
for _alias in ("орел", "орёл"):
    CITY_GEO_QUERY[_alias] = "Орёл"


def _geo_query_name(city: str) -> str:
    """Каноническое имя города для Geocoding API."""
    return CITY_GEO_QUERY.get(city.strip().lower(), city.strip())


def _bonus_photo(query: str, api_city_name: str = "") -> str | None:
    """Фото-пасхалка по тому городу, который уйдёт в прогноз."""
    names = [query.strip().lower(), api_city_name.strip().lower()]
    for city_normalized in names:
        if not city_normalized:
            continue
        if city_normalized in MOSCOW_ALIASES and MOSCOW_PHOTO_IDS:
            return random.choice(MOSCOW_PHOTO_IDS)
        if city_normalized in SPB_ALIASES and SPB_PHOTO_IDS:
            return random.choice(SPB_PHOTO_IDS)
        if city_normalized in NSK_ALIASES and NSK_PHOTO_IDS:
            return random.choice(NSK_PHOTO_IDS)
        if city_normalized in PERM_ALIASES and PERM_PHOTO_IDS:
            return random.choice(PERM_PHOTO_IDS)
    return None


def _bonus_gif(query: str, api_city_name: str = "") -> str | None:
    """Гиф-пасхалка по тому городу, который уйдёт в прогноз."""
    names = [query.strip().lower(), api_city_name.strip().lower()]
    for city_normalized in names:
        if not city_normalized:
            continue
        if city_normalized in ["орел", "орёл"] and OREL_GIF_IDS:
            return random.choice(OREL_GIF_IDS)
        if city_normalized == "россия" and RUSSIA_GIF_FILE_ID:
            return RUSSIA_GIF_FILE_ID
    return None


def _fetch_weather_html(city: str) -> tuple[str, str] | None:
    """Текст прогноза в HTML и имя города из API, либо None."""
    geo_name = _geo_query_name(city)

    # 1. Поиск координат через Geocoding API
    geo_res = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": geo_name, "count": 1, "language": "ru"},
        timeout=5,
    ).json()

    if not geo_res.get("results"):
        return None

    location = geo_res["results"][0]
    lat, lon = location["latitude"], location["longitude"]
    city_name = location.get("name", geo_name)
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

    return (
        f"<b>Погода в {city_name}</b> {country}\n\n"
        f"{emoji} <b>{desc}</b>\n"
        f"🌡️ Температура: <b>{temp}°C</b> (ощущается как {apparent}°C)\n"
        f"💨 Ветер: <b>{wind_speed} м/с</b>\n"
    ), city_name


def _inline_id() -> str:
    return uuid.uuid4().hex


async def weather_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инлайн: город пишется в поле ввода после @бота, в чат уходит только выбранный результат."""
    inline_query = update.inline_query
    if not inline_query:
        return

    city = (inline_query.query or "").strip()
    if not city:
        # Пустой запрос: без результатов, иначе «подсказка» уходит в чат как сообщение
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    try:
        fetched = _fetch_weather_html(city)
        text, api_city_name = fetched if fetched else (None, "")
        gif_id = _bonus_gif(city, api_city_name)
        if gif_id:
            gif_kwargs = {
                "id": _inline_id(),
                "mpeg4_file_id": gif_id,
                "title": f"Погода: {city}",
            }
            if text:
                gif_kwargs["caption"] = text
                gif_kwargs["parse_mode"] = "HTML"
            result = InlineQueryResultCachedMpeg4Gif(**gif_kwargs)
            await inline_query.answer([result], cache_time=30, is_personal=True)
            return

        if fetched is None:
            await inline_query.answer(
                [
                    InlineQueryResultArticle(
                        id=_inline_id(),
                        title=f"Город «{city}» не найден",
                        input_message_content=InputTextMessageContent(
                            f"❌ Город '{city}' не найден."
                        ),
                    )
                ],
                cache_time=5,
                is_personal=True,
            )
            return

        photo_id = _bonus_photo(city, api_city_name)
        if photo_id:
            result = InlineQueryResultCachedPhoto(
                id=_inline_id(),
                photo_file_id=photo_id,
                title=f"Погода: {city}",
                description="Отправить прогноз",
                caption=text,
                parse_mode="HTML",
            )
        else:
            result = InlineQueryResultArticle(
                id=_inline_id(),
                title=f"Погода: {city}",
                description="Отправить прогноз",
                input_message_content=InputTextMessageContent(text, parse_mode="HTML"),
            )
        await inline_query.answer([result], cache_time=30, is_personal=True)

    except Exception:
        await inline_query.answer(
            [
                InlineQueryResultArticle(
                    id=_inline_id(),
                    title="Не удалось получить погоду",
                    input_message_content=InputTextMessageContent(
                        "⚠️ Не удалось получить данные о погоде."
                    ),
                )
            ],
            cache_time=1,
            is_personal=True,
        )
