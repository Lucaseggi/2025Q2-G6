#!/bin/bash

# Services that need shared folder
SERVICES=("01-scraper" "02-processor" "03-embedder" "04-inserter")

# Folder names
SOURCE_FOLDER="shared"
TARGET_FOLDER="shared"

# Copy shared/ to each service
for service in "${SERVICES[@]}"; do
    if [ -d "$service" ]; then
        echo "Syncing to $service..."
        rm -rf "$service/$TARGET_FOLDER"
        cp -r "$SOURCE_FOLDER" "$service/$TARGET_FOLDER"
    else
        echo "Skipping $service (not found)"
    fi
done

echo "Done!"