# S3 Visualizer

Web-based browser for S3 bucket contents. Navigate folders and view JSON/text files.

## Quick Start

```bash
# Start with Docker Compose
docker compose up -d s3-visualizer

# Open in browser
http://localhost:5001
```

## Configuration

Edit `config.json` for custom settings:
```json
{
  "endpoint": "http://localstack:4566",
  "bucket": "simpla-cache",
  "access_key": "test",
  "secret_key": "test",
  "region": "us-east-1"
}
```

Pre-configured to work with LocalStack on the Docker network.
