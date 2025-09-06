FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY ./api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./api .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]