#!/usr/bin/env python3
"""
Power On Script for Samsung TV

Usage: python power_on.py <tv_id>
Checks TV power status and turns on the TV if it's off using Wake-on-LAN or power toggle.
"""

import sys
import time
from pathlib import Path
import wakeonlan
import json
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

def get_power_status(tv):
    """Get TV power status using rest_device_info"""
    tokens = load_tokens()
    token_data = tokens.get(tv['id'], {})
    token = token_data.get('token') if token_data else None
    
    if not token:
        print("Error: No token found for TV")
        return None
    
    samsung_tv = SamsungTVWS(
        host=tv['host'],
        port=tv.get('port', 8002),
        name="PowerStatusCheck",
        token=token,
        timeout=8
    )
    
    try:
        samsung_tv.open()
        device_info = samsung_tv.rest_device_info()
        samsung_tv.close()
        return device_info["device"]["PowerState"]
    except Exception as e:
        print(f"Error checking power status: {e}")
        try:
            samsung_tv.close()
        except:
            pass
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python power_on.py <tv_id>")
        sys.exit(1)
    
    tv_id = sys.argv[1]
    tvs = load_tv_config()
    tv = find_tv(tv_id, tvs)
    
    if not tv:
        print(f"Error: TV with ID '{tv_id}' not found in config")
        sys.exit(1)
    
    power_state = get_power_status(tv)
    if power_state is None:
        print("Error: Unable to retrieve power status")
        sys.exit(1)
    
    if power_state in ["on", "On"]:
        print("TV is already on. No action needed.")
    elif power_state == "standby":
        tokens = load_tokens()
        token_data = tokens.get(tv['id'], {})
        token = token_data.get('token') if token_data else None
        samsung_tv = SamsungTVWS(host=tv['host'], port=tv.get('port', 8002), token=token, timeout=8)
        try:
            samsung_tv.open()
            samsung_tv.shortcuts().power()
            samsung_tv.close()
            print("Power toggle sent for standby mode. Waiting 6 seconds to verify...")
            time.sleep(6)
            new_power_state = get_power_status(tv)
            if new_power_state in ["on", "On"]:
                print("Success: TV is now on.")
            else:
                print(f"Failure: TV is still {new_power_state}.")
        except Exception as e:
            print(f"Error sending power toggle: {e}")
            try:
                samsung_tv.close()
            except:
                pass
    elif power_state == "off":
        # Get MAC address from device_info (assuming we can retrieve it again or cache it)
        # For simplicity, re-fetch device_info to get MAC
        tokens = load_tokens()
        token_data = tokens.get(tv['id'], {})
        token = token_data.get('token') if token_data else None
        samsung_tv = SamsungTVWS(host=tv['host'], port=tv.get('port', 8002), token=token, timeout=8)
        try:
            samsung_tv.open()
            device_info = samsung_tv.rest_device_info()
            mac_address = device_info["device"]["wifiMac"]
            samsung_tv.close()
            wakeonlan.send_magic_packet(mac_address)
            print(f"Wake-on-LAN packet sent to {mac_address}. Waiting 6 seconds to verify...")
            time.sleep(6)
            new_power_state = get_power_status(tv)
            if new_power_state in ["on", "On"]:
                print("Success: TV is now on.")
            else:
                print(f"Failure: TV is still {new_power_state}.")
        except Exception as e:
            print(f"Error sending Wake-on-LAN: {e}")
            try:
                samsung_tv.close()
            except:
                pass
    else:
        print(f"Unknown power state: {power_state}")

if __name__ == "__main__":
    main()