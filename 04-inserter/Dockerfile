FROM python:3.11-slim

WORKDIR /app

COPY ./04-inserter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./04-inserter .

CMD ["python", "main.py"]