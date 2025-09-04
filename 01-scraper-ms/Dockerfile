FROM python:3.11-slim

WORKDIR /app

# Install certificates and curl for SSL verification
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

COPY ./01-scraper-ms/requirements.txt .
COPY ./shared/requirements.txt ./shared_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r shared_requirements.txt

COPY ./shared ./shared
COPY ./01-scraper-ms .

CMD ["python", "main.py"]