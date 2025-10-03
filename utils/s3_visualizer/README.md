# S3 Visualizer

Browse and visualize S3 bucket contents with support for JSON and plain text files.

## Quick Start

```bash
# Using Docker Compose (recommended)
docker-compose run --rm s3-visualizer your-bucket-name

# Using Python directly
pip install boto3
python s3_browser.py your-bucket-name
```

## Configuration

Pre-configured for LocalStack in `config.json`:
```json
{
  "endpoint": "http://localhost:4566",
  "access_key": "test",
  "secret_key": "test",
  "region": "us-east-1"
}
```

## Usage

```bash
# Interactive mode (default)
python s3_browser.py my-bucket

# Scan all objects
python s3_browser.py my-bucket --scan

# View specific file
python s3_browser.py my-bucket --view path/to/file.json

# Filter by prefix
python s3_browser.py my-bucket --prefix data/ --scan
```

## Interactive Commands

- `[number]` - View object by index
- `p [prefix]` - Change prefix filter
- `r` - Refresh
- `q` - Quit

## Advanced

```bash
# Custom endpoint
python s3_browser.py my-bucket --endpoint http://localhost:9000 --access-key key --secret-key secret

# Use AWS credentials (ignore config.json)
python s3_browser.py my-bucket --no-config
```
