FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Тут зберігатимуться .session файл і sqlite база - монтуй сюди volume
VOLUME ["/app/data"]

CMD ["python", "main.py"]
