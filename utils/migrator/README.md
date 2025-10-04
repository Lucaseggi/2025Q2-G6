# S3 ↔ Postgres Migrator

Bidirectional sync utility for `normas` table data between S3 (JSON format) and Postgres.

## Features

- **S3 → Postgres**: Scan S3 bucket, parse JSON files, bulk insert into normas table
- **Postgres → S3**: Export normas table to JSON (single file or multiple files)
- Handles JSONB fields and date serialization
- Batch processing with conflict resolution (upsert on infoleg_id)
- Dry-run mode to preview changes

## Quick Start

```bash
# Using Docker Compose
docker-compose run --rm migrator s3-to-pg my-bucket
docker-compose run --rm migrator pg-to-s3 my-bucket

# Using Python
pip install -r requirements.txt
python migrator.py s3-to-pg my-bucket
python migrator.py pg-to-s3 my-bucket
```

## Configuration

Pre-configured in `config.json` for LocalStack and local Postgres:

```json
{
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "simpla_rag",
    "user": "postgres",
    "password": "postgres"
  },
  "s3": {
    "endpoint": "http://localhost:4566",
    "access_key": "test",
    "secret_key": "test"
  }
}
```

## Usage

### S3 → Postgres

```bash
# Migrate all JSON files from bucket
python migrator.py s3-to-pg my-bucket

# Migrate with prefix filter
python migrator.py s3-to-pg my-bucket --prefix normas/

# Dry run (preview only)
python migrator.py s3-to-pg my-bucket --dry-run

# Custom batch size
python migrator.py s3-to-pg my-bucket --batch-size 500
```

### Postgres → S3

```bash
# Export to single JSON file
python migrator.py pg-to-s3 my-bucket --prefix export/

# Export to multiple files (one per record)
python migrator.py pg-to-s3 my-bucket --format multiple --prefix normas/

# Dry run
python migrator.py pg-to-s3 my-bucket --dry-run
```

## Schema

The migrator works with the `normas` table schema with fields including `infoleg_id` (unique), dates, JSONB arrays, and text fields.
