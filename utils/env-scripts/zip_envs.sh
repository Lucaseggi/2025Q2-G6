#!/bin/bash

# Script to collect all .env files from subdirectories and zip them with folder prefixes

ZIP_NAME="env_backup_$(date +%Y%m%d_%H%M%S).zip"
TEMP_DIR=$(mktemp -d)

echo "Collecting .env files..."

# Find all .env files in subdirectories (excluding the utils directory itself)
find . -name ".env" -type f ! -path "./utils/*" | while read -r env_file; do
    # Get the directory name (removing leading ./)
    dir_path=$(dirname "$env_file" | sed 's|^\./||')

    # Replace / with _ to create a flat namespace
    prefix=$(echo "$dir_path" | tr '/' '_')

    # Copy the file to temp directory with prefix
    cp "$env_file" "$TEMP_DIR/${prefix}.env"
    echo "  Added: $env_file as ${prefix}.env"
done

# Create the zip file
cd "$TEMP_DIR"
zip -q "$ZIP_NAME" *.env 2>/dev/null

if [ $? -eq 0 ]; then
    mv "$ZIP_NAME" "$OLDPWD/"
    echo ""
    echo "✓ Successfully created: $ZIP_NAME"
    echo "  Location: $(pwd)/$ZIP_NAME"
else
    echo "✗ Error: No .env files found or failed to create zip"
    cd "$OLDPWD"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Cleanup
cd "$OLDPWD"
rm -rf "$TEMP_DIR"
