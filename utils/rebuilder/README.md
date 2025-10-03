# Rebuilder

Builds and exposes the raw database extracted through scraping from Infoleg (norms up to 2021).

## Setup

1. Download `norms_dump` from [Drive](https://drive.google.com/drive/folders/1NX9Za0Mv_XjeYyFhMv7WP5X1bkZsjoGR?usp=sharing)
2. Place it in this directory
3. Start the service: `docker-compose up -d`

The Postgres database is:
- Exposed on host port **5450**
- Connected to the main `simpla_data_extraction_rag-network`
- Accessible from other services at `simpla_postgres:5432`

## Injecting Data into S3 Cache

To populate the scraper's S3 cache (`simpla-cache`) with existing normas:

```bash
# From utils/migrator directory
docker compose run --rm migrator pg-to-s3 simpla-cache \
  --pg-host simpla_postgres \
  --pg-database simpla \
  --format multiple \
  --prefix norms/
```

This exports all normas from the rebuilder database to S3 as individual JSON files with keys matching the scraper's cache format: `norms/{infoleg_id}.json`

See `utils/queries` for useful database queries.
