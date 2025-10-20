#!/usr/bin/env python3
"""
Example control script for Samsung TVs

Usage: python control_tv.py <tv_id> <command>
Returns: success, failed, or id_not_found
"""

import json
import sys
import time
import os
from pathlib import Path
from samsungtvws import SamsungTVWS

# Get the project root directory (parent of scripts)
PROJECT_ROOT = Path(__file__).parent.parent


def load_tv_config():
    """Load TV configuration from config/config.json"""
    config_path = PROJECT_ROOT / "config" / "config.json"
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
            return config['tvs']
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_tokens():
    """Load tokens from tokens.json"""
    tokens_path = PROJECT_ROOT / "tokens.json"
    try:
        with open(tokens_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def find_tv(tv_id, tvs):
    """Find TV by ID"""
    for tv in tvs:
        if tv['id'] == tv_id:
            return tv
    return None


def control_tv(tv, command):
    """Send control command to TV"""
    try:
        # Load token if available
        tokens = load_tokens()
        token_data = tokens.get(tv['id'], {})
        token = token_data.get('token') if token_data else None
        
        samsung_tv = SamsungTVWS(
            host=tv['host'],
            port=tv['port'],
            name="Samsung TV Controller",
            token=token,
            timeout=10
        )
        
        # Send the command
        samsung_tv.send_key(command)
        samsung_tv.close()
        return True
        
    except Exception:
        return False


def main():
    """Main function"""
    if len(sys.argv) != 3:
        print("control_failed")
        sys.exit(1)
    
    tv_id = sys.argv[1]
    command = sys.argv[2]
    tvs = load_tv_config()
    
    # Find TV
    tv = find_tv(tv_id, tvs)
    if not tv:
        print("id_not_found")
        sys.exit(1)
    
    # Send control command
    if control_tv(tv, command):
        print("control_success")
    else:
        print("control_failed")


if __name__ == "__main__":
    main()