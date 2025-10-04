# Processor Microservice API

Document processor service with S3 caching and replay functionality.

## Endpoints

### Health Check
```http
GET /health
```

### Replay Documents

#### Single Document
```http
POST /replay
{
  "infoleg_id": 183532,
  "version": "latest"
}
```

#### Multiple Documents
```http
POST /replay/batch
{
  "documents": [
    {"infoleg_id": 183532, "version": "latest"},
    {"infoleg_id": 183533}
  ]
}
```

### Cache Information
```http
GET /cache/info/183532
```

## Response Format

**Success:**
```json
{
  "status": "success",
  "message": "Successfully replayed document 183532 to embedding queue",
  "infoleg_id": 183532,
  "version": "v1",
  "source": "cache"
}
```

**Batch Response:**
```json
{
  "status": "completed",
  "success_count": 2,
  "failed_count": 0,
  "total_count": 2,
  "results": [...]
}
```

**Error:**
```json
{
  "status": "error",
  "message": "No cached data found for document 183532",
  "reason": "cache_miss"
}
```

## Usage Examples

```bash
# Single document replay
curl -X POST http://processor:8004/replay \
  -H "Content-Type: application/json" \
  -d '{"infoleg_id": 183532}'

# Batch replay
curl -X POST http://processor:8004/replay/batch \
  -H "Content-Type: application/json" \
  -d '{"documents": [{"infoleg_id": 183532}, {"infoleg_id": 183533}]}'

# Check cache info
curl http://processor:8004/cache/info/183532
```

## Testing

**Run all tests:**
```bash
docker run --rm --env-file .env --user $(id -u):$(id -g) -v "$PWD:/host" -v "$PWD/prompts:/app/prompts:ro" --workdir /host processor-test python test_runner.py
```

**Render htmls:**
```bash
docker run --rm --env-file .env --user $(id -u):$(id -g) -v "$PWD:/host" --workdir /host processor-test python test_diff_viewer.py
```

**Run single test:**
```bash
docker run --rm --env-file .env --user $(id -u):$(id -g) -v "$PWD:/host" -v "$PWD/prompts:/app/prompts:ro" --workdir /host processor-test python test_runner.py --test-id 180781
```

Results include `actual.json`, `comparison_report.txt`, and `visual_diff.html` in each test directory.