#!/usr/bin/env python3
"""
Samsung TV Power Status Script - PowerState Detection

Usage: python power_status.py <tv_id>
Returns: PowerState values from Samsung TV:
  - "on" - TV is fully powered on
  - "standby" - TV is in standby mode
  - "sleep" - TV is completely off (no network response)
  - "unreachable" - TV not found or network error
"""

import json
import sys
import socket
import subprocess
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
    """Load tokens from tokens.json"""
    tokens_path = PROJECT_ROOT / "tokens.json"
    try:
        with open(tokens_path, 'r') as file:
            return json.load(file)
    except:
        return {}

def find_tv(tv_id, tvs):
    """Find TV by ID"""
    for tv in tvs:
        if tv.get('id') == tv_id:
            return tv
    return None

def safe_call(func, timeout_seconds=5):
    """Safely call a function with timeout"""
    result = {}
    exception = {}
    
    def target():
        try:
            result['value'] = func()
        except Exception as e:
            exception['error'] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        return None, Exception(f"Timeout after {timeout_seconds}s")
    
    if 'error' in exception:
        return None, exception['error']
    
    return result.get('value'), None

def get_websocket_power_state(host, port, token):
    """Get PowerState from WebSocket device info"""
    def get_power_state():
        tv = SamsungTVWS(host=host, port=port, name="PowerCheck", token=token, timeout=4)
        tv.open()
        device_info = tv.rest_device_info()
        tv.close()
        
        if device_info and 'device' in device_info:
            power_state = device_info['device'].get('PowerState', 'unknown')
            return power_state.lower()  # Convert to lowercase for consistency
        return None
    
    result, error = safe_call(get_power_state, timeout_seconds=6)
    return result if result else None

def check_ping(host):
    """Network ping test to detect standby/sleep difference"""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '2', host], 
            capture_output=True, 
            text=True, 
            timeout=4
        )
        return result.returncode == 0
    except:
        return False

def check_power_status(tv):
    """
    Check TV power status with Samsung PowerState detection
    
    Detection Logic:
    1. Try WebSocket -> Get actual PowerState ("on", "standby", etc.)
    2. If WebSocket fails but ping succeeds -> "standby" 
    3. If ping fails -> "sleep"
    4. If TV not found -> "unreachable"
    """
    host = tv['host']
    port = tv.get('port', 8002)
    tokens = load_tokens()
    token = tokens.get(tv['id'], {}).get('token')
    
    # Method 1: Get PowerState from WebSocket (most accurate)
    if token:
        power_state = get_websocket_power_state(host, port, token)
        if power_state:
            # Return the actual PowerState from Samsung TV
            return power_state
    
    # Method 2: WebSocket failed, try ping to distinguish standby vs sleep
    if check_ping(host):
        # TV responds to network but not WebSocket = likely standby
        return "standby"
    
    # Method 3: No network response = completely off
    return "sleep"

def main():
    if len(sys.argv) != 2:
        print("unreachable")
        sys.exit(1)
    
    tv_id = sys.argv[1]
    tvs = load_tv_config()
    tv = find_tv(tv_id, tvs)
    
    if not tv:
        print("unreachable")
        sys.exit(1)
    
    try:
        power_state = check_power_status(tv)
        print(power_state)
    except Exception:
        print("unreachable")

if __name__ == "__main__":
    main()