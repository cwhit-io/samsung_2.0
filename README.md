# Samsung TV Controller API

A comprehensive FastAPI application for managing Samsung Smart TVs through WebSocket and HTTP APIs. Features concurrent processing, power status monitoring, TV pairing, and a generic script execution framework for extensible TV control operations.

## 🚀 Features

- **🔌 TV Pairing**: Automated Samsung TV pairing with token management
- **⚡ Power Status Monitoring**: Real-time power state detection (`on`, `standby`, `sleep`)
- **🔄 Concurrent Processing**: Execute operations on multiple TVs simultaneously
- **🛠️ Generic Script Executor**: Zero-maintenance framework for adding new TV scripts
- **📊 RESTful API**: Complete FastAPI implementation with automatic documentation
- **🔒 Error Handling**: Robust timeout and error management
- **📝 Comprehensive Logging**: Detailed execution tracking and debugging

## 📁 Project Structure

```
samsung_2.0/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/endpoints/
│   │   └── tv.py              # TV control API endpoints
│   ├── models/
│   │   └── tv.py              # Pydantic data models
│   └── services/
│       └── tv_service.py      # Business logic layer
├── scripts/
│   ├── pair_tv.py             # TV pairing script
│   ├── power_status.py        # Power status detection script
│   ├── control_tv.py          # TV control commands script
│   └── tv_info_collector.py   # Comprehensive TV information gathering
├── config/
│   └── config.json            # TV configuration database
├── logs/                      # Script execution logs
├── tokens.json                # Pairing authentication tokens
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.8+
- Samsung Smart TV on the same network
- TV's IP address and MAC address

### 1. Clone and Setup Environment
```bash
git clone <repository-url>
cd samsung_2.0

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Your TVs
Update `config/config.json` with your TV information:
```json
{
  "tvs": [
    {
      "id": "living_room_tv",
      "name": "Living Room Samsung TV",
      "host": "192.168.1.100",
      "port": 8002,
      "mac_address": "AA:BB:CC:DD:EE:FF"
    }
  ]
}
```

### 3. Start the API Server
```bash
cd samsung_2.0
uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

### 4. Access the API Documentation
- **Interactive Docs**: http://127.0.0.1:8002/docs
- **Alternative Docs**: http://127.0.0.1:8002/redoc
- **OpenAPI Schema**: http://127.0.0.1:8002/openapi.json

## 📡 API Endpoints

### Core TV Operations

#### List All TVs
```bash
GET /api/v1/tv/list
```
Returns all configured TVs with pairing status.

#### Pair TVs
```bash
POST /api/v1/tv/pair
Content-Type: application/json

{
  "tv_ids": ["living_room_tv", "bedroom_tv"]
}
```

#### Generic Script Executor
```bash
# Method 1: Script name in body
POST /api/v1/tv/execute
{
  "script_name": "power_status",
  "tv_ids": ["living_room_tv", "bedroom_tv"],
  "concurrent": true
}

# Method 2: Script name in URL
POST /api/v1/tv/execute/power_status
{
  "tv_ids": ["living_room_tv"],
  "args": ["optional", "arguments"]
}
```

## 🔧 Available Scripts

### Power Status Monitoring
```bash
# Check power status of multiple TVs
curl -X POST http://127.0.0.1:8002/api/v1/tv/execute \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "power_status",
    "tv_ids": ["living_room_tv", "bedroom_tv"]
  }'

# Response includes: "on", "standby", "sleep", "unreachable"
```

### TV Control
```bash
# Send control commands
curl -X POST http://127.0.0.1:8002/api/v1/tv/execute/control_tv \
  -H "Content-Type: application/json" \
  -d '{
    "tv_ids": ["living_room_tv"],
    "args": ["KEY_POWER"]
  }'
```

### Information Gathering
```bash
# Collect comprehensive TV information
python scripts/tv_info_collector.py living_room_tv
# Results saved to logs/tv_info_<tv_id>_<timestamp>.log
```

## 🎯 Power Status Detection

The power status system uses multiple detection methods:

1. **WebSocket Device Info** (Primary) - Queries Samsung TV's PowerState field
2. **Network Ping** (Fallback) - Detects network connectivity
3. **Port Scanning** - Checks service availability

**Power States:**
- **`on`** - TV fully powered and responsive
- **`standby`** - TV in standby mode (network active, services limited)
- **`sleep`** - TV completely off (no network response)
- **`unreachable`** - TV not found or network error

## 🔄 Concurrent Processing

The system supports concurrent execution for multiple TVs:

```bash
# Process 5 TVs simultaneously
{
  "script_name": "power_status",
  "tv_ids": ["tv1", "tv2", "tv3", "tv4", "tv5"],
  "concurrent": true
}

# Response includes execution times for each TV
{
  "total_requested": 5,
  "execution_time_seconds": 2.34,
  "results": [...]
}
```

## 🚀 Adding New Scripts

The generic script executor makes adding new functionality effortless:

### 1. Create Your Script
```python
#!/usr/bin/env python3
# scripts/my_new_script.py

import sys
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("USAGE_ERROR")
        sys.exit(1)
    
    tv_id = sys.argv[1]
    # Your TV logic here
    print("SUCCESS")

if __name__ == "__main__":
    main()
```

### 2. Use Immediately via API
```bash
# No code changes needed!
curl -X POST http://127.0.0.1:8002/api/v1/tv/execute/my_new_script \
  -d '{"tv_ids": ["living_room_tv"]}'
```

## 📊 Response Format

All scripts return consistent response format:

```json
{
  "script_name": "power_status",
  "total_requested": 2,
  "results": [
    {
      "tv_id": "living_room_tv",
      "status": "success",
      "output": "on",
      "success": true,
      "timestamp": "2025-10-20T14:52:56.320320"
    }
  ],
  "summary": "Executed 'power_status' on 2 TVs in 1.23s: 2 successful",
  "execution_time_seconds": 1.23,
  "concurrent": true
}
```

## 🔒 Error Handling

The system includes comprehensive error handling:

- **Timeout Protection** - Scripts timeout after 30 seconds
- **Invalid TV IDs** - Validates all TV IDs before execution
- **Script Not Found** - Returns 404 for missing scripts  
- **Network Errors** - Graceful handling of connection failures
- **Concurrent Safety** - Thread-safe execution with proper cleanup

## 📝 Logging

- **API Logs** - FastAPI automatic request/response logging
- **Script Logs** - Individual script execution details in `logs/` directory
- **Error Tracking** - Comprehensive error capture and reporting

## 🔧 Development

### Running Tests
```bash
# Test individual scripts
python scripts/power_status.py living_room_tv

# Test API endpoints
curl -X GET http://127.0.0.1:8002/api/v1/tv/list
```

### Adding Dependencies
```bash
pip install new-package
pip freeze > requirements.txt
```

## 🤝 Contributing

1. Add new scripts to `scripts/` directory
2. Follow the established response format
3. Scripts automatically work via generic executor
4. No API code changes required for new scripts

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Samsung TV integration via [samsungtvws](https://github.com/xchwarze/samsung-tv-ws-api)
- Concurrent processing with Python's `ThreadPoolExecutor`