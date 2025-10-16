# Populate - Process Norms by titulo_sumario

Queries the Postgres database (from rebuilder) for norms matching specific `titulo_sumario` values and processes them through the RAG pipeline.

## Target titulo_sumario Values

The script processes norms with the following titles:
- **ADUANAS**
- **IMPORTACIONES**
- **COMERCIO EXTERIOR**
- **SERVICIOS ADUANEROS**
- **SERVICIO EXTERIOR**
- **TARIFAS**
- **EXPORTACIONES**
- **ARANCELES**

## Prerequisites

1. **Main services must be running:**
   ```bash
   cd ../..
   docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
   ```

2. **Rebuilder must be running:**
   ```bash
   cd ../rebuilder
   docker compose up -d
   cd ../populate
   ```

3. **Migrator should have been run** (optional but recommended):
   ```bash
   cd ../migrator
   docker compose run --rm migrator pg-to-s3
   cd ../populate
   ```

## Usage

### Basic Usage (Default Settings)

```bash
docker compose run --rm populate
```

This uses default settings:
- Postgres host: `simpla_postgres` (rebuilder database)
- Postgres port: `5432`
- Postgres database: `simpla`
- API endpoint: `http://scraper:8003/process`
- Delay: 10 seconds between requests

### Custom Settings

You can override any parameter:

```bash
# Force reprocessing of already processed norms
docker compose run --rm populate --force

# Reduce delay between requests (faster processing)
docker compose run --rm populate --delay 5

# Use different database
docker compose run --rm populate \
  --pg-host postgres-db \
  --pg-port 5432 \
  --pg-database simpla_rag
```

### Available Options

```bash
docker compose run --rm populate --help
```

Options:
- `--api-url`: Process API endpoint (default: http://scraper:8003/process)
- `--delay`: Delay in seconds between requests (default: 10)
- `--force`: Force reprocessing of already processed norms
- `--pg-host`: Postgres host (default: simpla_postgres)
- `--pg-port`: Postgres port (default: 5432)
- `--pg-database`: Postgres database (default: simpla)
- `--pg-user`: Postgres user (default: postgres)
- `--pg-password`: Postgres password (default: postgres)

## How It Works

1. **Connects to Postgres** database (rebuilder instance)
2. **Queries for norms** matching target titulo_sumario values
3. **Sends each norm** to the scraper process endpoint
4. **Waits** specified delay between requests to avoid overloading
5. **Displays progress** with success/failure counts
6. **Shows summary** with statistics

## Output Example

```
================================================================================
Processing Norms by titulo_sumario
================================================================================
API Endpoint:    http://scraper:8003/process
Force reprocess: False
Delay:           10s between requests
Target titles:   ADUANAS, IMPORTACIONES, COMERCIO EXTERIOR, ...

✓ Found 1250 norms matching target titulo_sumario values

================================================================================
Starting Processing
================================================================================

[1/1250] Processing norm 66648 (Acordada - ADUANAS)... ✓ SUCCESS
[2/1250] Processing norm 96480 (Acta - IMPORTACIONES)... ✓ SUCCESS
[3/1250] Processing norm 136102 (Actuacion - COMERCIO EXTERIOR)... ✓ SUCCESS
...
[1250/1250] Processing norm 402995 (Resolución - ARANCELES)... ✓ SUCCESS

================================================================================
SUMMARY
================================================================================
Total:        1250
Success:      1248
Failed:       2
Success rate: 99.84%
Time elapsed: 3h 28m 30s
Avg per norm: 10.0s
```

## Processing Pipeline

When a norm is processed:

1. **Scraper** (8003): Fetches/uses cached norm data from S3
2. **Purifier** (8004): Cleans HTML and fixes orthography
3. **Processor** (8005): Structures the legal text using LLM
4. **Embedder** (8001): Generates vector embeddings
5. **Inserter**: Stores in OpenSearch and Postgres

## Monitoring

### Check Progress
```bash
# View populate container logs
docker compose logs populate

# View scraper logs
cd ../..
docker compose logs -f scraper

# View processor logs (main bottleneck)
docker compose logs -f processor-worker
```

### Check Queue Status
Open RabbitMQ UI: http://localhost:15672 (admin/admin123)

### Check Database
```bash
# Connect to main postgres
docker exec -it postgres-db psql -U postgres -d simpla_rag

# Check processed count
SELECT COUNT(*) FROM normas_structured;

# Check recent processing
SELECT infoleg_id, tipo_norma, titulo_sumario, inserted_at
FROM normas_structured
ORDER BY inserted_at DESC
LIMIT 10;
```

## Troubleshooting

### "Connection refused" errors
Ensure main services are running:
```bash
cd ../..
docker compose ps
```

### "Database connection failed"
Ensure rebuilder is running:
```bash
cd ../rebuilder
docker compose ps
```

### High failure rate
- Check scraper logs for errors
- Verify S3 cache has data (run migrator first)
- Check if API endpoint is accessible

### Slow processing
- Reduce `--delay` (but monitor system resources)
- Scale up processor workers in docker-compose.production.yml
- Check if LLM API (Gemini) is rate-limiting

## Notes

- Processing large datasets can take hours depending on:
  - Number of norms matching target titles
  - Delay between requests
  - LLM processing speed
  - System resources

- The script is idempotent - rerunning it will skip already processed norms (unless `--force` is used)

- Recommended to run in a `tmux` or `screen` session for long-running operations
