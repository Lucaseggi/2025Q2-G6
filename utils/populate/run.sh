#!/bin/bash
#
# Run populate script in Docker container
# Queries norms by titulo_sumario and processes them through the pipeline
#

set -e

cd "$(dirname "$0")"

echo "================================================================================"
echo "Populate - Process Norms by titulo_sumario"
echo "================================================================================"
echo ""

# Check if main services are running
if ! docker compose -f ../../docker-compose.yml ps | grep -q "scraper"; then
    echo "⚠ Warning: Main services don't appear to be running"
    echo "Please start them first:"
    echo "  cd ../.."
    echo "  docker compose -f docker-compose.yml -f docker-compose.production.yml up -d"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Check if rebuilder is running
if ! docker ps | grep -q "simpla_postgres"; then
    echo "⚠ Warning: Rebuilder database doesn't appear to be running"
    echo "Please start it first:"
    echo "  cd ../rebuilder"
    echo "  docker compose up -d"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo "Starting populate script..."
echo ""

# Run populate container with all arguments passed through
docker compose run --rm populate "$@"

echo ""
echo "================================================================================"
echo "✓ Populate script completed"
echo "================================================================================"
