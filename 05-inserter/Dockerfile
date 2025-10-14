FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY . .

# Generate Python gRPC stubs from proto files
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/relational.proto
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/vectorial.proto

# Create logs directory for structured logging
RUN mkdir -p /app/logs && chmod 777 /app/logs

CMD ["python", "-u", "main.py"]