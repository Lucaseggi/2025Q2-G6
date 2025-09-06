FROM python:3.11-slim

WORKDIR /app

COPY ./02-processing-ms/requirements.txt .
COPY ./shared/requirements.txt ./shared_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r shared_requirements.txt

COPY ./shared ./shared
COPY ./02-processing-ms .

CMD ["python", "processor.py"]