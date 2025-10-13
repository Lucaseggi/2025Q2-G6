# S3 ↔ Postgres Migrator

Bidirectional sync utility for `normas` table between S3 (`norms/` prefix, wrapped JSON format) and Postgres.

## Features

- **Postgres → S3**: Export normas table to individual wrapped JSON files in `norms/`
- **S3 → Postgres**: Import wrapped JSON files from `norms/` into normas table
- Handles JSONB fields and date serialization
- Batch processing with conflict resolution (upsert on infoleg_id)
- Idempotent operations

## Usage

```bash
# Export Postgres to S3
docker compose run --rm migrator pg-to-s3

# Import S3 to Postgres
docker compose run --rm migrator s3-to-pg

# Custom batch size for import
docker compose run --rm migrator s3-to-pg --batch-size 500
```

## JSON Format

Files are stored in `norms/{infoleg_id}.json` with this structure:

```json
{
  "cached_at": "2025-10-04T17:33:00.727549",
  "cache_version": "1.0",
  "data": {
    "scraping_data": {
      "infoleg_response": {
        "infoleg_id": "...",
        "jurisdiccion": "...",
        ...
      }
    }
  }
}
```
