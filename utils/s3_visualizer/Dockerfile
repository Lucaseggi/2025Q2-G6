FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir boto3

# Copy application files
COPY s3_browser.py .
COPY config.json .

# Make script executable
RUN chmod +x s3_browser.py

ENTRYPOINT ["python", "s3_browser.py"]
