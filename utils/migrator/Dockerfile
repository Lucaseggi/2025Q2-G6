FROM python:3.11-slim

WORKDIR /app

# Install ping for debugging
RUN apt-get update && apt-get install -y iputils-ping curl && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY migrator.py .
COPY config.json .
COPY test_connectivity.sh .

# Make scripts executable
RUN chmod +x migrator.py test_connectivity.sh

ENTRYPOINT ["python", "migrator.py"]
