# Simpla Data Extraction - Legal RAG Pipeline

A microservices-based RAG (Retrieval-Augmented Generation) system for processing Argentine legal documents from InfoLEG.

## Cloud Deploy

### Prerequisites
- **Terraform installed**: Download from [terraform.io](https://www.terraform.io/downloads)
- **AWS CLI installed**: Follow the installation for your OS following [these instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **AWS credentials configured**: Set up `$HOME/.aws/credentials` with your access and secret keys:
  ```
  [default]
  aws_access_key_id = your-access-key
  aws_secret_access_key = your-secret-key
  ```

### Deploying

Go to `terraform-lambda` folder and run `deploy.sh`:
```bash
cd terraform-lambda
```

Deploy architecture (this process may take around 30 minutes):
```bash
./deploy.sh
```

Scrape some norms (this process may take a few minutes):
```bash
./invoke-scraper-batch.sh
```

And check the front using the urls in the output of the terraform!

##### Extras

You can monitor the lambda logs meanwhile, for example the inserter with:
```bash
aws logs tail /aws/lambda/simpla-inserter --since 5m --format short --region us-east-1 | tail -30
```

If you wish to scrape any specific norm you can make a direct invoke to the scraper Lambda:
```bash
cat > /tmp/test-scrape.json << 'EOF'
{
  "httpMethod": "POST",
  "path": "/scrape",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"infoleg_id\": 183532, \"force\": false}"
}
EOF
```
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

### Local Deploy

There are three Docker Compose files which can be used additively, `docker-compose.yml` is the base file, with `docker-compose.production.yaml` you can add replicas and lastly with `docker-compose.logging.yaml` you can add a logging environment.

So a quick run can be made with:
```bash
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml up
```

And if you are attempting to scrape a large batch of norms then the full version is recommended, mostly due to the replicas:

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml -f docker-compose.logging.yml build
docker compose -f docker-compose.yml -f docker-compose.production.yml -f docker-compose.logging.yml up
```

After deploying scraping can be manually activated for a specific norm with:
```bash
curl --location 'http://localhost:8003/scrape' \
--header 'Content-Type: application/json' \
--data '{
    "infoleg_id": 183532,
    "force": false
}'
```

And finally a question to the RAG with:
```bash
curl --location 'http://localhost:8042/question' \
--header 'Content-Type: application/json' \
--data '{
    "question": "Que me podes decir sobre la bandera argentina?"
}'
```