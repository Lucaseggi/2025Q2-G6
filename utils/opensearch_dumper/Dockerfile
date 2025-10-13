FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dump_opensearch.py .

# Create output directory
RUN mkdir -p /dumps

ENTRYPOINT ["python", "dump_opensearch.py"]
CMD ["--help"]
