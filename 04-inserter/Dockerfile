FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate Python gRPC stubs from proto files
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/relational.proto
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/vectorial.proto

CMD ["python", "main.py"]