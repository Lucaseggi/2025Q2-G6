FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY 00-shared/requirements.txt ./shared_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r shared_requirements.txt

COPY 00-shared ./00-shared
COPY . .

CMD ["python", "main.py"]