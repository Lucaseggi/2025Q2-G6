# Scraper Microservice API

Enhanced scraper service for InfoLEG documents with S3 caching.

## Endpoints

### Health Check
```http
GET /health
```

### Scrape Documents `/scrape`

Checks cache, if not present, scrapes. Never sends into processing queue.

#### Single Document
```http
POST /scrape
{
  "infoleg_id": 183532,
  "force": false
}
```

#### Range of Documents
```http
POST /scrape
{
  "start_id": 183530,
  "end_id": 183540,
  "max_docs": 10,
  "force": false
}
```

**Parameters:**
- `force` - Override cache (default: false)
- `max_docs` - Range limit (default: 10, max: 100)

### Processing `/process`

Forces fresh scraping and sends to processing queue.

```http
POST /process
{
  "infoleg_id": 183532
}
```

```http
POST /process
{
  "start_id": 183530,
  "end_id": 183540,
  "max_docs": 10
}
```

### Cache Management

#### Statistics
```http
GET /cache/stats
```

#### List Cached Documents
```http
GET /cache/list?limit=100
```

## Response Format

**Success (Fresh Scrape):**
```json
{
  "status": "success",
  "message": "Successfully scraped norm 183532",
  "infoleg_id": 183532,
  "source": "scraped",
  "cache_hit": false,
  "forced": false,
  "timestamp": "2024-01-01T10:00:00"
}
```

**Success (Cache Hit):**
```json
{
  "status": "cached",
  "message": "Norm 183532 served from cache",
  "infoleg_id": 183532,
  "source": "cache",
  "cache_hit": true,
  "forced": false,
  "timestamp": "2024-01-01T10:00:00"
}
```

**Range Response:**
```json
{
  "status": "completed",
  "scraped_count": 5,
  "cached_count": 3,
  "failed_count": 0,
  "results": [...]
}
```

**Error:**
```json
{
  "status": "error",
  "message": "Error description",
  "reason": "api_failed|cache_send_failed|..."
}
```

## Usage Examples

```bash
# Single document
curl -X POST http://scraper:8003/scrape \
  -H "Content-Type: application/json" \
  -d '{"infoleg_id": 183532}'

# Force refresh
curl -X POST http://scraper:8003/process \
  -H "Content-Type: application/json" \
  -d '{"infoleg_id": 183532}'

# Range scraping
curl -X POST http://scraper:8003/scrape \
  -H "Content-Type: application/json" \
  -d '{"start_id": 183530, "end_id": 183535}'
```