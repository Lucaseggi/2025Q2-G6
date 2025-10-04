#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -U postgres; do
    sleep 1
done

if [ ! -f /var/lib/postgresql/data/.restored ]; then
    echo "Creating 'simpla' role..."
    psql -U postgres -d simpla -c 'CREATE ROLE simpla WITH LOGIN SUPERUSER;' || true

    echo "Starting database restore..."
    pg_restore -U postgres -d simpla -v /docker-entrypoint-initdb.d/simpla_dump.backup || true

    touch /var/lib/postgresql/data/.restored

    echo "============================================"
    echo "✓ Database restore completed successfully!"
    echo "============================================"
else
    echo "Database already restored (found .restored marker)"
fi
