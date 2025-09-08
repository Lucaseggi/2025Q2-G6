# Simpla Data Extraction - Legal RAG Pipeline

A microservices-based RAG (Retrieval-Augmented Generation) system for processing Argentine legal documents from InfoLEG.

## Quick Start

### 1. Start the Services
```bash
docker-compose up --build
```

### 2. Scrape a Legal Document
```bash
curl -X POST http://localhost:8003/scrape \
  -H "Content-Type: application/json" \
  -d '{"infoleg_id": 183532}'
```

### 3. Verify Document in Vector Database
```bash
curl -X GET "http://localhost:9200/documents/_count"
```

### 4. Query the RAG API
```bash
curl -X POST http://localhost:8000/api/questions/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Cuales son las regulaciones de la bandera argentina?"}'
```

## Services Overview
- **Scraper** (8003): Fetches documents from InfoLEG API
- **Processing**: Processes and structures legal text  
- **Embedding** (8001): Creates vector embeddings using Gemini
- **Inserter**: Stores documents in OpenSearch vector database
- **API** (8000): RAG question-answering interface
- **OpenSearch** (9200): Vector database
- **LocalStack** (4566): AWS services emulation (SQS)

That's it! The pipeline automatically processes the scraped document and makes it searchable via the RAG API.
## Environment Setup

### Required Environment Files

Each microservice requires its own `.env` file with service-specific variables:

If you are from my team you can get them [here](https://drive.google.com/drive/folders/1XEpPmQm6z2dnG0xC7MYaAdGQx2zoRG0F?usp=drive_link) :)).

**`00-localstack/.env`**
```bash
DOCKER_HOST=unix:///var/run/docker.sock
```

**`01-scraper/.env`**
```bash
# AWS/LocalStack Configuration
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test  
AWS_DEFAULT_REGION=us-east-1
SQS_ENDPOINT=http://localstack:4566

# Queue URLs
PROCESSING_QUEUE_URL=http://localstack:4566/000000000000/processing-queue

# Service Configuration
SCRAPE_MODE=service
SCRAPER_PORT=8003
DEBUG=0
```

**`02-processor/.env`**
```bash
# AWS/LocalStack Configuration  
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
SQS_ENDPOINT=http://localstack:4566

# Queue URLs
PROCESSING_QUEUE_URL=http://localstack:4566/000000000000/processing-queue
EMBEDDING_QUEUE_URL=http://localstack:4566/000000000000/embedding-queue

# Gemini API Key (REQUIRED - get from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your-gemini-api-key-here

DEBUG=0
```

**`03-embedder/.env`**
```bash
# AWS/LocalStack Configuration
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1  
SQS_ENDPOINT=http://localstack:4566

# Queue URLs
EMBEDDING_QUEUE_URL=http://localstack:4566/000000000000/embedding-queue
INSERTING_QUEUE_URL=http://localstack:4566/000000000000/inserting-queue

# Gemini API Key (REQUIRED - get from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your-gemini-api-key-here

# Service Configuration
EMBEDDING_PORT=8001
DEBUG=0
```

**`04-inserter/.env`**
```bash
# AWS/LocalStack Configuration
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
SQS_ENDPOINT=http://localstack:4566

# Queue URLs  
INSERTING_QUEUE_URL=http://localstack:4566/000000000000/inserting-queue

# OpenSearch Configuration
OPENSEARCH_ENDPOINT=http://opensearch:9200

DEBUG=0
```

**`api/.env`**
```bash
# Django Configuration
SECRET_KEY=django-insecure-j&j1gu^=pfd*mgyam-gw3dab3nkpyxoz8vaptvb1nf-%o1csr_
DEBUG=0

# External Service URLs
EMBEDDING_SERVICE_URL=http://embedder:8001
OPENSEARCH_ENDPOINT=http://opensearch:9200

# Gemini API Key (REQUIRED - get from https://aistudio.google.com/app/apikey) 
GEMINI_API_KEY=your-gemini-api-key-here

# Service Configuration
API_PORT=8000
```

**`opensearch-db/.env`**
```bash
# OpenSearch Database Environment Variables
cluster.name=opensearch-cluster
node.name=opensearch-node
discovery.type=single-node
bootstrap.memory_lock=true

# Java Memory Settings
OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g

# Security Configuration (disabled for development)
DISABLE_INSTALL_DEMO_CONFIG=true
DISABLE_SECURITY_PLUGIN=true
```

### ⚠️ Important: Gemini API Keys

You **MUST** replace `your-gemini-api-key-here` with actual Gemini API keys in:
- `02-processor/.env`
- `03-embedder/.env` 
- `api/.env`

Get your API keys from: https://aistudio.google.com/app/apikey
