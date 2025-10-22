#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
FUNCTION_NAME="simpla-scraper"
REGION="${AWS_REGION:-us-east-1}"
FORCE="${FORCE:-false}"

# Array of infoleg IDs to scrape
ids=(183532 405520 405903 21841 410436)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Batch Scraper Lambda Invocation${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Function: ${FUNCTION_NAME}"
echo -e "Region: ${REGION}"
echo -e "Force: ${FORCE}"
echo -e "Total IDs: ${#ids[@]}"
echo -e "${BLUE}========================================${NC}\n"

# Counter for statistics
SUCCESS_COUNT=0
FAILED_COUNT=0

for id in "${ids[@]}"; do
  echo -e "${YELLOW}Scraping infoleg_id=$id...${NC}"

  # Create payload file in current directory
  cat > "test-scrape-${id}.json" << EOF
{
  "httpMethod": "POST",
  "path": "/scrape",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"infoleg_id\": ${id}, \"force\": ${FORCE}}"
}
EOF

  # Invoke Lambda function
  if aws lambda invoke \
    --function-name "${FUNCTION_NAME}" \
    --payload "fileb://test-scrape-${id}.json" \
    --region "${REGION}" \
    --cli-read-timeout 0 \
    --cli-connect-timeout 0 \
    "response-${id}.json" 2>&1 | tee "invoke-output-${id}.txt"; then

    echo -e "${GREEN}✓ Lambda invoked${NC}"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))

    # Display response
    echo "Response:"
    cat "response-${id}.json" | jq '.' 2>/dev/null || cat "response-${id}.json"

  else
    echo -e "${RED}✗ Failed to invoke Lambda${NC}"
    echo "Error details:"
    cat "invoke-output-${id}.txt"
    FAILED_COUNT=$((FAILED_COUNT + 1))
  fi

  # Cleanup temp files
  rm -f "test-scrape-${id}.json" "response-${id}.json" "invoke-output-${id}.txt"

  echo -e "${BLUE}-------------------------------------------${NC}\n"

  # Optional: Add delay to avoid throttling
  # sleep 1
done

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Batch processing complete!${NC}"
echo -e "Successful: ${SUCCESS_COUNT}/${#ids[@]}"
echo -e "Failed: ${FAILED_COUNT}/${#ids[@]}"
echo -e "${BLUE}========================================${NC}"
