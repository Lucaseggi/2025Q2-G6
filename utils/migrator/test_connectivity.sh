#!/bin/bash

echo "=== Testing Network Connectivity ==="
echo ""

echo "Testing Postgres (simpla_postgres:5432)..."
ping -c 2 simpla_postgres || echo "Ping failed (this is normal if ICMP is disabled)"
curl -v telnet://simpla_postgres:5432 2>&1 | head -5
echo ""

echo "Testing LocalStack (localstack:4566)..."
ping -c 2 localstack || echo "Ping failed (this is normal if ICMP is disabled)"
curl -v http://localstack:4566/_localstack/health
echo ""

echo "Testing from Python..."
python3 << 'EOF'
import boto3
import os

# Test S3 connection
try:
    s3_client = boto3.client(
        's3',
        endpoint_url='http://localstack:4566',
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-1'
    )
    buckets = s3_client.list_buckets()
    print(f"✓ S3 connection successful! Buckets: {[b['Name'] for b in buckets.get('Buckets', [])]}")
except Exception as e:
    print(f"✗ S3 connection failed: {e}")

# Test Postgres connection
try:
    import psycopg2
    conn = psycopg2.connect(
        host='simpla_postgres',
        port=5432,
        database='simpla',
        user='postgres',
        password='postgres'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM normas")
    count = cursor.fetchone()[0]
    print(f"✓ Postgres connection successful! Records in normas table: {count}")
    conn.close()
except Exception as e:
    print(f"✗ Postgres connection failed: {e}")
EOF
