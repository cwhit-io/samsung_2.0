#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🔍 Samsung TV WebSocket Device Info Collector${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if specific TV ID is provided
if [ "$1" ]; then
    echo -e "${YELLOW}📺 Getting device info for TV: $1${NC}"
    echo ""
    
    curl -X POST http://127.0.0.1:8002/api/v1/tv/execute \
      -H "Content-Type: application/json" \
      -d "{
        \"script_name\": \"get_tv_info\",
        \"tv_ids\": [\"$1\"],
        \"concurrent\": false
      }" --silent | python -m json.tool
else
    echo -e "${YELLOW}📺 Getting device info for ALL TVs (this may take a moment)...${NC}"
    echo ""
    
    curl -X POST http://127.0.0.1:8002/api/v1/tv/execute \
      -H "Content-Type: application/json" \
      -d '{
        "script_name": "get_tv_info",
        "tv_ids": [
          "b4_tv", "m2_tv", "b3_tv", "m4_tv", "t1_tv",
          "t4_tv", "m3_tv", "t3_tv", "m1_tv", "t2_tv", 
          "b1_tv", "t5_tv", "b2_tv", "m5_tv", "b5_tv"
        ],
        "concurrent": true
      }' --silent | python -m json.tool
fi

echo ""
echo -e "${GREEN}✅ Device info collection completed!${NC}"
echo ""
echo -e "${PURPLE}💡 Usage:${NC}"
echo -e "  ${CYAN}./helpers/get_tv_info.sh${NC}           - Get info from all TVs"
echo -e "  ${CYAN}./helpers/get_tv_info.sh m2_tv${NC}     - Get info from specific TV"
echo ""
echo -e "${PURPLE}📊 Info includes:${NC}"
echo -e "  • Power State (on/standby)"
echo -e "  • Model & Firmware"
echo -e "  • Network Type & IP"
echo -e "  • Resolution & Capabilities"
echo -e "  • WiFi MAC Address"