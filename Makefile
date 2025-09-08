.PHONY: build up down logs clean restart test

# Build all services
build:
	docker compose build

# Start all services
up:
	docker compose up -d

# Stop all services  
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# View logs for specific service
logs-scraper:
	docker compose logs -f scraper-ms

logs-processing:
	docker compose logs -f processing-ms

logs-embedding:
	docker compose logs -f embedding-ms

logs-inserter:
	docker compose logs -f inserter-ms

logs-localstack:
	docker compose logs -f localstack

logs-opensearch:
	docker compose logs -f opensearch

logs-django:
	docker compose logs -f django-api

logs-frontend:
	docker compose logs -f frontend-app

# Clean up containers and volumes
clean:
	docker compose down -v
	docker system prune -f

# Restart all services
restart: down up

# Show service status
status:
	docker compose ps

# Execute shell in service container
shell-scraper:
	docker compose exec scraper-ms /bin/bash

shell-processing:
	docker compose exec processing-ms /bin/bash

shell-embedding:
	docker compose exec embedding-ms /bin/bash

shell-inserter:
	docker compose exec inserter-ms /bin/bash

shell-frontend:
	docker compose exec frontend-app /bin/sh

# Check OpenSearch health
check-opensearch:
	curl -X GET "http://localhost:9200/_cluster/health?pretty"

# Check LocalStack queues
check-queues:
	docker compose exec localstack awslocal sqs list-queues

# Create queues manually if needed
create-queues:
	docker compose exec localstack awslocal sqs create-queue --queue-name processing-queue
	docker compose exec localstack awslocal sqs create-queue --queue-name embedding-queue  
	docker compose exec localstack awslocal sqs create-queue --queue-name inserting-queue

# Build and run in one command
dev: build up logs