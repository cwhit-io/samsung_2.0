#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}⚡ Samsung TV Power Status Checker${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# Check if specific TV ID is provided
if [ "$1" ]; then
    echo -e "${YELLOW}📺 Checking power status for TV: $1${NC}"
    echo ""
    
    curl -X POST http://127.0.0.1:8002/api/v1/tv/execute \
      -H "Content-Type: application/json" \
      -d "{
        \"script_name\": \"power_status\",
        \"tv_ids\": [\"$1\"],
        \"concurrent\": false
      }" --silent | python -c "
import json, sys
data = json.load(sys.stdin)
for result in data['results']:
    status = result['output']
    tv_id = result['tv_id']
    if status == 'on':
        print(f'🟢 {tv_id}: ON')
    elif status == 'standby':
        print(f'🟡 {tv_id}: STANDBY') 
    elif status == 'sleep':
        print(f'🔴 {tv_id}: SLEEP')
    else:
        print(f'❌ {tv_id}: {status.upper()}')
"
else
    echo -e "${YELLOW}📺 Checking power status for ALL TVs...${NC}"
    echo ""
    
    curl -X POST http://127.0.0.1:8002/api/v1/tv/execute \
      -H "Content-Type: application/json" \
      -d '{
        "script_name": "power_status",
        "tv_ids": [
          "b4_tv", "m2_tv", "b3_tv", "m4_tv", "t1_tv",
          "t4_tv", "m3_tv", "t3_tv", "m1_tv", "t2_tv", 
          "b1_tv", "t5_tv", "b2_tv", "m5_tv", "b5_tv"
        ],
        "concurrent": true
      }' --silent | python -c "
import json, sys
data = json.load(sys.stdin)
print('Power Status Summary:')
print('=' * 25)
on_count = standby_count = sleep_count = error_count = 0
for result in sorted(data['results'], key=lambda x: x['tv_id']):
    status = result['output']
    tv_id = result['tv_id']
    if status == 'on':
        print(f'🟢 {tv_id}: ON')
        on_count += 1
    elif status == 'standby':
        print(f'🟡 {tv_id}: STANDBY')
        standby_count += 1
    elif status == 'sleep':
        print(f'🔴 {tv_id}: SLEEP')
        sleep_count += 1
    else:
        print(f'❌ {tv_id}: {status.upper()}')
        error_count += 1

print()
print(f'📊 Summary: {on_count} ON, {standby_count} STANDBY, {sleep_count} SLEEP, {error_count} ERRORS')
print(f'⏱️  Completed in {data[\"execution_time_seconds\"]:.2f}s')
"
fi

echo ""
echo -e "${PURPLE}💡 Usage:${NC}"
echo -e "  ${CYAN}./helpers/check_power_status.sh${NC}         - Check all TVs"
echo -e "  ${CYAN}./helpers/check_power_status.sh m2_tv${NC}   - Check specific TV"