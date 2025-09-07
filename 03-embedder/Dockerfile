FROM python:3.11-slim

WORKDIR /app

COPY ./03-embedder/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./03-embedder .

CMD ["python", "main.py"]