FROM python:3.11-slim

WORKDIR /app

# Install certificates and curl for SSL verification
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

COPY requirements.txt .
COPY 00-shared/requirements.txt ./shared_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r shared_requirements.txt

COPY 00-shared ./00-shared
COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8003", "--workers", "2", "api:app"]