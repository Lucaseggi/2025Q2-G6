#!/bin/bash

# Script to extract .env files from a zip and place them in their original directories

if [ $# -eq 0 ]; then
    echo "Usage: $0 <env_backup.zip>"
    echo ""
    echo "This script extracts .env files from a backup zip and places them"
    echo "in their corresponding directories based on the filename prefix."
    exit 1
fi

ZIP_FILE="$1"

if [ ! -f "$ZIP_FILE" ]; then
    echo "✗ Error: File not found: $ZIP_FILE"
    exit 1
fi

TEMP_DIR=$(mktemp -d)

echo "Extracting .env files from $ZIP_FILE..."

# Extract zip to temp directory
unzip -q "$ZIP_FILE" -d "$TEMP_DIR"

if [ $? -ne 0 ]; then
    echo "✗ Error: Failed to extract zip file"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Process each .env file in the temp directory
cd "$TEMP_DIR"
for env_file in *.env; do
    if [ ! -f "$env_file" ]; then
        continue
    fi

    # Remove .env extension to get the prefix
    prefix="${env_file%.env}"

    # Convert underscores back to slashes to get directory path
    dir_path=$(echo "$prefix" | tr '_' '/')

    # Create the directory if it doesn't exist
    mkdir -p "$OLDPWD/$dir_path"

    # Copy the .env file to its destination
    cp "$env_file" "$OLDPWD/$dir_path/.env"
    echo "  Restored: $dir_path/.env"
done

echo ""
echo "✓ Successfully restored .env files"

# Cleanup
cd "$OLDPWD"
rm -rf "$TEMP_DIR"
