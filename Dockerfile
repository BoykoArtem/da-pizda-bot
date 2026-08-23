FROM python:3.10-slim

WORKDIR /app

# Сначала копируем только requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Затем копируем весь остальной код
COPY . .

CMD ["python", "bot.py"]