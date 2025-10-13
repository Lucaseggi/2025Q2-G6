FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY . .

# Create logs directory for structured logging
RUN mkdir -p /app/logs && chmod 777 /app/logs

CMD ["python", "main.py"]