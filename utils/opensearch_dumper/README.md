# OpenSearch Database Dumper

Export your entire OpenSearch vector database to a file, including embeddings.

## Installation

```bash
cd utils/opensearch_dumper
pip install -r requirements.txt
```

## Usage

### From Docker Host (when containers are running)

```bash
# NDJSON format (recommended - preserves all data including vectors)
python dump_opensearch.py --host localhost --port 9200 --index documents --format ndjson --output opensearch_dump.ndjson

# CSV format (good for Excel/spreadsheet analysis)
python dump_opensearch.py --host localhost --port 9200 --index documents --format csv --output opensearch_dump.csv

# Parquet format (compressed, best for very large datasets)
python dump_opensearch.py --host localhost --port 9200 --index documents --format parquet --output opensearch_dump.parquet
```

### From Inside Docker Network

```bash
# Add this service to docker-compose.yml temporarily:
dumper:
  build: ./utils/opensearch_dumper
  container_name: opensearch-dumper
  volumes:
    - ./dumps:/dumps
  networks:
    - rag-network
  command: >
    python dump_opensearch.py
    --host opensearch
    --port 9200
    --index documents
    --format ndjson
    --output /dumps/opensearch_dump.ndjson

# Then run:
docker compose run --rm dumper
```

## Output Formats

### NDJSON (Newline-Delimited JSON)
- **Best for:** Full data preservation with vectors
- **Size:** Largest (uncompressed)
- **Use case:** Complete backup, re-importing to OpenSearch
- **Example line:**
```json
{"_id": "12345", "_index": "documents", "embedding": [0.1, 0.2, ...], "infoleg_id": 183532, "content": "..."}
```

### CSV
- **Best for:** Spreadsheet analysis (Excel, Google Sheets)
- **Size:** Medium
- **Use case:** Data analysis, filtering, quick inspection
- **Note:** Embeddings stored as JSON strings in a column

### Parquet
- **Best for:** Large datasets (millions of documents)
- **Size:** Smallest (compressed)
- **Use case:** Data science, analytics with Pandas/Spark
- **Compression:** Snappy compression (typically 5-10x smaller than JSON)

## Performance

- Uses OpenSearch scroll API for memory-efficient streaming
- Processes ~1,000-5,000 documents/second (depends on network/disk)
- Can handle millions of documents without running out of memory

## Re-importing Data

To restore the data back to OpenSearch:

```python
from opensearchpy import OpenSearch, helpers

client = OpenSearch([{'host': 'localhost', 'port': 9200}])

def load_ndjson(filename):
    with open(filename, 'r') as f:
        for line in f:
            doc = json.loads(line)
            doc_id = doc.pop('_id')
            doc.pop('_index')
            yield {
                '_index': 'documents',
                '_id': doc_id,
                '_source': doc
            }

# Bulk import
helpers.bulk(client, load_ndjson('opensearch_dump.ndjson'))
```

## File Sizes (Estimated)

For 100,000 documents with 768-dimensional embeddings:
- NDJSON: ~800 MB - 1.5 GB
- CSV: ~1 GB - 2 GB (due to JSON serialization overhead)
- Parquet: ~150 MB - 300 MB (compressed)

## Troubleshooting

**Connection refused:**
```bash
# Make sure OpenSearch is running
curl http://localhost:9200/_cluster/health
```

**Index doesn't exist:**
```bash
# List all indices
curl http://localhost:9200/_cat/indices
```

**Out of memory:**
- Use Parquet format (most memory-efficient)
- The script uses streaming, so it shouldn't need much RAM
- If dumping to CSV fails, use NDJSON instead
