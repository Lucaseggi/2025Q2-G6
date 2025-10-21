#!/bin/bash
set -e

echo "Building Lambda JARs using Docker..."

# Convert Windows path to Unix path for Docker
WORK_DIR="$(cd .. && pwd -W 2>/dev/null || pwd)"

# Build relational-guard
echo "Building relational-guard..."
# Use MSYS_NO_PATHCONV to prevent Git Bash from converting /app path
MSYS_NO_PATHCONV=1 docker run --rm -v "/$(echo $WORK_DIR | sed 's|\\|/|g' | sed 's|:||')/06-relational-guard:/app" -w /app maven:3.9-eclipse-temurin-17 \
  mvn clean package -DskipTests -f pom-lambda.xml

mkdir -p lambda-artifacts
cp ../06-relational-guard/target/relational-guard-1.0.0.jar lambda-artifacts/

# Build vectorial-guard
echo "Building vectorial-guard..."
# Use MSYS_NO_PATHCONV to prevent Git Bash from converting /app path
MSYS_NO_PATHCONV=1 docker run --rm -v "/$(echo $WORK_DIR | sed 's|\\|/|g' | sed 's|:||')/07-vectorial-guard:/app" -w /app maven:3.9-eclipse-temurin-17 \
  mvn clean package -DskipTests -f pom-lambda.xml

cp ../07-vectorial-guard/target/vectorial-guard-1.0.0.jar lambda-artifacts/

echo "✓ Lambda JARs built and copied to lambda-artifacts/"
