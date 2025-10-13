FROM python:3.11-slim

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY requirements.txt .
COPY shared/requirements.txt ./shared_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r shared_requirements.txt

COPY shared ./shared
COPY . .

# Create logs directory for structured logging
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Change ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8004

CMD ["python", "main.py"]