FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

COPY requirements.txt .
COPY shared/requirements.txt ./shared_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r shared_requirements.txt

COPY shared ./shared
COPY . .

# Create logs directory for structured logging
RUN mkdir -p /app/logs && chmod 777 /app/logs

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8004"]
