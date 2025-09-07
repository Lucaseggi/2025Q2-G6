FROM python:3.11-slim

WORKDIR /app

# Install certificates and curl for SSL verification
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

COPY ./01-scraper/requirements.txt .
COPY ./00-shared/requirements.txt ./shared_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r shared_requirements.txt

COPY ./00-shared ./00-shared
COPY ./01-scraper .

CMD ["python", "main.py"]