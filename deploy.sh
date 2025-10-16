#!/bin/bash
#
# Deployment script for simpla_data_extraction to production server
# Target: ansible@192.168.0.192:2221
#
# Usage: ./deploy.sh [destination_path]
#   destination_path: Remote directory (default: ~/simpla_data_extraction)
#

set -e

# Configuration
REMOTE_HOST="192.168.0.192"
REMOTE_PORT="2221"
REMOTE_USER="ansible"
REMOTE_PATH="${1:-~/simpla_data_extraction}"
LOCAL_PATH="$(cd "$(dirname "$0")" && pwd)"

echo "================================================================================"
echo "Simpla Data Extraction - Production Deployment"
echo "================================================================================"
echo "Source:      $LOCAL_PATH"
echo "Destination: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PORT:$REMOTE_PATH"
echo ""

# Confirm before proceeding
read -p "Continue with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Step 1: Syncing project files to remote server..."
echo "--------------------------------------------------------------------------------"

rsync -avz --progress -e "ssh -p $REMOTE_PORT" \
    --exclude '.git/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '*.pyo' \
    --exclude '.venv/' \
    --exclude 'venv/' \
    --exclude 'node_modules/' \
    --exclude '.DS_Store' \
    --exclude 'test_outputs/' \
    --exclude '*.log' \
    --exclude '.terraform/' \
    --exclude 'terraform.tfstate*' \
    --exclude '.idea/' \
    --exclude '.vscode/' \
    --exclude '03-processor/test/' \
    --exclude 'frontend/dist/' \
    --exclude 'frontend/node_modules/' \
    "$LOCAL_PATH/" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"

echo ""
echo "✓ Files synced successfully"
echo ""
echo "================================================================================"
echo "Next steps (run on remote server $REMOTE_HOST):"
echo "================================================================================"
echo ""
echo "1. SSH into the server:"
echo "   ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"
echo ""
echo "2. Navigate to project directory:"
echo "   cd $REMOTE_PATH"
echo ""
echo "3. Start services in production mode:"
echo "   docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build"
echo ""
echo "4. Run the rebuilder (restore database from dump):"
echo "   cd utils/rebuilder"
echo "   # Ensure norms_dump file is present (download from Drive if needed)"
echo "   docker compose up -d"
echo "   cd ../.."
echo ""
echo "5. Run the migrator (export Postgres data to S3):"
echo "   cd utils/migrator"
echo "   docker compose run --rm migrator pg-to-s3"
echo "   cd ../.."
echo ""
echo "6. Run the populate script (process norms by titulo_sumario):"
echo "   docker compose -f utils/populate/docker-compose.yml run --rm populate"
echo ""
echo "7. Monitor logs:"
echo "   docker compose logs -f"
echo ""
echo "================================================================================"
echo "✓ Deployment preparation complete!"
echo "================================================================================"
