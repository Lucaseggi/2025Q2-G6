# Simpla Data Extraction - Legal RAG Pipeline

A microservices-based RAG (Retrieval-Augmented Generation) system for processing Argentine legal documents from InfoLEG.

## Cloud Deploy

### Quick Test Commands

Monitor inserter logs:
```bash
aws logs tail /aws/lambda/simpla-inserter --since 5m --format short --region us-east-1 | tail -30
```

Invoke scraper Lambda:
```bash
aws lambda invoke --function-name simpla-scraper --payload fileb:///tmp/scrape-183532.json --region us-east-1 /tmp/scraper-response3.json
cat /tmp/scraper-response3.json
```

Test embedder Lambda (health check):
```bash
aws lambda invoke \
  --function-name simpla-embedder \
  --payload '{"httpMethod":"GET","path":"/health"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/embedder-health.json
cat /tmp/embedder-health.json | jq -r '.body' | jq '.'
```

Test embedder Lambda (generate embedding):
```bash
aws lambda invoke \
  --function-name simpla-embedder \
  --payload '{"httpMethod":"POST","path":"/embed","body":"{\"text\":\"Test legal document about Argentine regulations\"}"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/embedder-embed.json
cat /tmp/embedder-embed.json | jq -r '.body' | jq '{model, dimensions, timestamp, embedding_sample: .embedding[0:5]}'
```

### Prerequisites
- **Terraform installed**: Download from [terraform.io](https://www.terraform.io/downloads)
- **AWS CLI installed**: Follow the installation for your OS following [these instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **AWS credentials configured**: Set up `$HOME/.aws/credentials` with your access and secret keys:
  ```
  [default]
  aws_access_key_id = your-access-key
  aws_secret_access_key = your-secret-key
  ```

### Deploy to AWS
```bash
cd terraform
terraform init
chmod +x *.sh
./run.sh
cd ../frontend
npm run build
BUCKET_NAME=$(cd ../terraform && terraform output -raw frontend_bucket_name)
aws s3 sync ./dist/ s3://$BUCKET_NAME --delete
```

#### Access the Frontend
After deployment, get the frontend URL:
```bash
cd terraform
terraform output frontend_website_url
```

### Test the Deployment

#### 1. Scrape a Document
SSH into the scraper instance and trigger a scrape:
```bash
ssh -F ~/.ssh/terraform_config scraper
curl -X POST http://localhost:8003/scrape \
  -H "Content-Type: application/json" \
  -d '{"infoleg_id": 183532}'
```

#### 2. Query the RAG API
Get the bastion host IP from your SSH config:
```bash
grep -A1 "Host bastion" ~/.ssh/terraform_config | grep HostName | awk '{print $2}'
```

Then query the API using the bastion IP:
```bash
BASTION_IP=$(grep -A1 "Host bastion" ~/.ssh/terraform_config | grep HostName | awk '{print $2}')
curl -X POST http://$BASTION_IP:8000/api/questions/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Cuales son las regulaciones de la bandera argentina?"}'
```

## Run Configurations

### 1. Development (Default)
Single instance of each service, no scaling.

```bash
docker compose up --build
```

### 2. Development with Logging
Single instance + Loki/Grafana for log aggregation.

```bash
docker compose -f docker-compose.yml -f docker-compose.logging.yml up --build
```

Access Grafana: http://localhost:3000 (admin/admin)

### 3. Production (Scaled)
Optimized for large datasets with horizontal scaling:
- 2 Purifier Workers
- 4 Processor Workers
- 2 Embedder Workers
- 2 Inserter Workers

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml up --build
```

### 4. Production with Logging (Recommended)
Production scaling + centralized logging.

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml -f docker-compose.logging.yml up --build
```

Access Grafana: http://localhost:3000 (admin/admin)

### 5. Partial Pipeline (Until Inserter)
Run only the processing pipeline without the storage guards. Useful for testing the data processing flow.

**Background mode (detached):**
```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml up --build \
  localstack \
  opensearch \
  scraper \
  purifier-worker \
  purifier-api \
  processor-worker \
  processor-api \
  embedder-worker \
  embedder-api \
  inserter
```

> **Note:** The inserter requires relational-guard and vectorial-guard to fully process data. Without them, messages will queue in SQS but won't be stored.

## Service Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| **Scraper API** | http://localhost:8003 | Document scraping |
| **Purifier API** | http://localhost:8004 | HTML purification |
| **Processor API** | http://localhost:8005 | Document structuring |
| **Embedder API** | http://localhost:8001 | Embedding generation |
| **Main API** | http://localhost:8010 | RAG query interface |
| **RabbitMQ UI** | http://localhost:15672 | Queue management (admin/admin123) |
| **OpenSearch** | http://localhost:9200 | Vector database |
| **Grafana** | http://localhost:3000 | Logs & monitoring (admin/admin) |


## Services Overview
- **Scraper** (8003): Fetches documents from InfoLEG API
- **Processing**: Processes and structures legal text  
- **Embedding** (8001): Creates vector embeddings using Gemini
- **Inserter**: Stores documents in OpenSearch vector database
- **API** (8000): RAG question-answering interface
- **OpenSearch** (9200): Vector database
- **LocalStack** (4566): AWS services emulation (SQS)

## Environment Setup

### Required Environment Files

Each microservice requires its own `.env` file with service-specific variables:

If you are from my team you can get them [here](https://drive.google.com/drive/folders/1XEpPmQm6z2dnG0xC7MYaAdGQx2zoRG0F?usp=drive_link) :)).

There are scripts for zipping and unzipping the .envs at /utils/env-scripts.