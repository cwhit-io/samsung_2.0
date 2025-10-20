#!/usr/bin/env python3
"""
Samsung TV WebSocket Device Info Script

Usage: python get_tv_info.py <tv_id>
Returns: JSON formatted device info from WebSocket including current display info
"""

import json
import sys
import threading
from pathlib import Path
from samsungtvws import SamsungTVWS

PROJECT_ROOT = Path(__file__).parent.parent

def load_tv_config():
    """Load TV configuration"""
    config_path = PROJECT_ROOT / "config" / "config.json"
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
            return config['tvs']
    except:
        return []

def load_tokens():
    """Load tokens"""
    tokens_path = PROJECT_ROOT / "tokens.json"
    try:
        with open(tokens_path, 'r') as file:
            return json.load(file)
    except:
        return {}

def find_tv(tv_id, tvs):
    """Find TV by ID"""
    for tv in tvs:
        if tv['id'] == tv_id:
            return tv
    return None

def safe_websocket_call(func, timeout_seconds=8):
    """Execute WebSocket call with timeout"""
    result = {}
    exception = {}
    
    def target():
        try:
            result['data'] = func()
        except Exception as e:
            exception['error'] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        return None, "timeout"
    
    if 'error' in exception:
        return None, str(exception['error'])
    
    return result.get('data'), None

def get_comprehensive_tv_info(tv):
    """Get comprehensive TV info including current display status"""
    tokens = load_tokens()
    token_data = tokens.get(tv['id'], {})
    token = token_data.get('token') if token_data else None
    
    if not token:
        return "no_token"
    
    samsung_tv = SamsungTVWS(
        host=tv['host'],
        port=tv.get('port', 8002),
        name="ComprehensiveInfoQuery",
        token=token,
        timeout=8
    )
    
    try:
        samsung_tv.open()
        
        # Collect all available information
        tv_info = {
            "tv_id": tv['id'],
            "tv_name": tv['name'],
            "host": tv['host'],
            "port": tv['port']
        }
        
        # 1. Basic device info (REST call, no timeout needed)
        print("\033[92mDevice Info (from rest_device_info):\033[0m")
        try:
            device_info = samsung_tv.rest_device_info()
            tv_info["device_info"] = device_info
            print(json.dumps(device_info, indent=2))
        except Exception as e:
            tv_info["device_info_error"] = str(e)
            print(f"\033[91mError: {str(e)}\033[0m")
        
        # 2. Available applications
        print("\033[93mAvailable Apps (from app_list):\033[0m")
        def get_app_list():
            return samsung_tv.app_list()
        app_list, error = safe_websocket_call(get_app_list, timeout_seconds=15)  # Increased timeout to 15 seconds
        if app_list:
            tv_info["available_apps"] = app_list
            print(json.dumps(app_list, indent=2))
        else:
            tv_info["available_apps_error"] = error or "timeout"
            print(f"\033[91mError: {error or 'timeout'}\033[0m")
        
        # Note: Current input cannot be retrieved with the available library methods
        tv_info["current_input"] = "unknown"
        print("\033[91mCurrent Input: Unable to retrieve with this library version\033[0m")
        
        samsung_tv.close()
        return json.dumps(tv_info, indent=2)
        
    except Exception as e:
        try:
            samsung_tv.close()
        except:
            pass
        return f"websocket_error: {e}"

def main():
    if len(sys.argv) != 2:
        print("usage_error")
        sys.exit(1)
    
    tv_id = sys.argv[1]
    tvs = load_tv_config()
    tv = find_tv(tv_id, tvs)
    
    if not tv:
        print("id_not_found")
        sys.exit(1)
    
    result = get_comprehensive_tv_info(tv)
    # Optionally, print the full JSON at the end with a header
    print("\033[90mFull JSON Result:\033[0m")
    print(result)

if __name__ == "__main__":
    main()