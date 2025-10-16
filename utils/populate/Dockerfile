FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir psycopg2-binary requests

# Copy populate script
COPY populate.py /app/

# Make script executable
RUN chmod +x /app/populate.py

# Run populate script
ENTRYPOINT ["python", "/app/populate.py"]
