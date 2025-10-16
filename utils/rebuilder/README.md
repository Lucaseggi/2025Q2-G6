# Rebuilder

Builds and exposes the raw database extracted through scraping from Infoleg (norms up to 2021).

## Prerequisites

The rebuilder requires the main `simpla_data_extraction_rag-network` Docker network to exist:

```bash
# Option 1: Start from project root (creates network automatically)
cd ../..
docker compose up -d

# Option 2: Create network manually
docker network create simpla_data_extraction_rag-network
```

## Setup

1. Download `norms_dump` from [Drive](https://drive.google.com/drive/folders/1NX9Za0Mv_XjeYyFhMv7WP5X1bkZsjoGR?usp=sharing)
2. Place it in this directory (`utils/rebuilder/`)
3. Start the service:
   ```bash
   cd utils/rebuilder
   docker compose up -d
   ```

The Postgres database is:
- Exposed on host port **5450** (to avoid conflict with main stack's postgres on 5432)
- Connected to the main `simpla_data_extraction_rag-network`
- Accessible from other services at `simpla_postgres:5432`

## Troubleshooting

If you get a "network not found" error:
```bash
# Remove any dangling containers
docker rm simpla_postgres

# Ensure the network exists
docker network ls | grep simpla_data_extraction_rag-network

# If missing, create it
docker network create simpla_data_extraction_rag-network
```

## Injecting Data into S3 Cache

To populate the scraper's S3 storage with existing normas, use the migrator utility:

```bash
# Ensure rebuilder is running
cd utils/rebuilder
docker compose up -d

# Export from rebuilder database to S3
cd ../migrator
docker compose run --rm migrator
```

This exports all normas from the rebuilder database to LocalStack S3 as individual JSON files with keys matching the scraper's cache format: `norms/{infoleg_id}.json`

See `utils/queries` for useful database queries.
