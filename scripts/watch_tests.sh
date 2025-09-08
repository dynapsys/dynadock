#!/bin/bash

echo "Starting test watch mode..."
LAST_HASH=""

while true; do
    # Calculate a hash of the files in tests/ and src/ to detect changes
    CURRENT_HASH=$(find tests/ src/ -type f -name "*.py" -exec md5sum {} \; | sort | md5sum | awk '{print $1}')
    
    if [ "$CURRENT_HASH" != "$LAST_HASH" ]; then
        echo "File change detected. Running tests..."
        uv run pytest tests/ -v
        LAST_HASH="$CURRENT_HASH"
    fi
    sleep 2
done
