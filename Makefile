.PHONY: build build-logs build-prod build-prod-logs up down logs clean restart test up-logs up-prod up-prod-logs dev dev-logs dev-prod dev-prod-logs help stats info grafana

# Show available commands
help:
	@echo "=== SimplA Data Extraction - Makefile Commands ==="
	@echo ""
	@echo "QUICK START:"
	@echo "  make dev              - Build and run in development mode with logs"
	@echo "  make dev-logs         - Build and run with Grafana logging (http://localhost:3000)"
	@echo "  make dev-prod         - Build and run in production mode (scaled workers)"
	@echo "  make dev-prod-logs    - Build and run in production mode with logging (RECOMMENDED)"
	@echo ""
	@echo "BUILD COMMANDS:"
	@echo "  make build            - Build all services (development)"
	@echo "  make build-logs       - Build with logging configuration"
	@echo "  make build-prod       - Build with production configuration"
	@echo "  make build-prod-logs  - Build with production + logging"
	@echo ""
	@echo "START/STOP COMMANDS:"
	@echo "  make up               - Start services in development mode"
	@echo "  make up-logs          - Start services with logging"
	@echo "  make up-prod          - Start services in production mode"
	@echo "  make up-prod-logs     - Start services in production with logging"
	@echo "  make down             - Stop all services"
	@echo "  make restart          - Restart all services"
	@echo ""
	@echo "LOGS & MONITORING:"
	@echo "  make logs             - View logs from all services"
	@echo "  make logs-scraper     - View scraper logs"
	@echo "  make logs-processing  - View processing logs"
	@echo "  make logs-embedding   - View embedding logs"
	@echo "  make logs-inserter    - View inserter logs"
	@echo "  make grafana          - Show Grafana access information"
	@echo "  make stats            - Show container resource usage"
	@echo "  make info             - Show detailed service information"
	@echo ""
	@echo "MAINTENANCE:"
	@echo "  make clean            - Stop services and remove volumes"
	@echo "  make status           - Show service status"
	@echo ""
	@echo "INFRASTRUCTURE CHECKS:"
	@echo "  make check-opensearch - Check OpenSearch health"
	@echo "  make check-queues     - List SQS queues"
	@echo "  make create-queues    - Create required SQS queues"
	@echo ""
	@echo "SHELL ACCESS:"
	@echo "  make shell-scraper    - Open shell in scraper container"
	@echo "  make shell-processing - Open shell in processing container"
	@echo "  make shell-embedding  - Open shell in embedding container"
	@echo "  make shell-inserter   - Open shell in inserter container"
	@echo "  make shell-frontend   - Open shell in frontend container"

# Build all services (development mode)
build:
	docker compose build

# Build all services with logging configuration
build-logs:
	docker compose -f docker-compose.yml -f docker-compose.logging.yml build

# Build all services with production configuration
build-prod:
	docker compose -f docker-compose.yml -f docker-compose.production.yml build

# Build all services with production and logging configuration
build-prod-logs:
	docker compose -f docker-compose.yml -f docker-compose.production.yml -f docker-compose.logging.yml build

# Start all services (development mode)
up:
	docker compose up -d

# Start all services with logging infrastructure (Loki + Grafana)
up-logs:
	docker compose -f docker-compose.yml -f docker-compose.logging.yml up -d

# Start all services in production mode (with scaling and resource limits)
up-prod:
	docker compose -f docker-compose.yml -f docker-compose.production.yml up -d

# Start all services in production mode with logging (RECOMMENDED for large datasets)
up-prod-logs:
	docker compose -f docker-compose.yml -f docker-compose.production.yml -f docker-compose.logging.yml up -d

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

# Build and run in one command (development mode)
dev: build up logs

# Build and run with logging infrastructure
dev-logs: build-logs up-logs
	@echo "Grafana dashboard available at http://localhost:3000 (admin/admin)"
	docker compose -f docker-compose.yml -f docker-compose.logging.yml logs -f

# Build and run in production mode
dev-prod: build-prod up-prod logs

# Build and run in production mode with logging (RECOMMENDED)
dev-prod-logs: build-prod-logs up-prod-logs
	@echo "Grafana dashboard available at http://localhost:3000 (admin/admin)"
	docker compose -f docker-compose.yml -f docker-compose.production.yml -f docker-compose.logging.yml logs -f

# Quick helpers
grafana:
	@echo "Opening Grafana at http://localhost:3000"
	@echo "Username: admin"
	@echo "Password: admin"

# Show resource usage for all containers
stats:
	docker stats --no-stream

# Show detailed service information
info:
	@echo "=== Service Status ==="
	docker compose ps
	@echo ""
	@echo "=== Resource Usage ==="
	docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"