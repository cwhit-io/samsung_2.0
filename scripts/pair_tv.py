#!/usr/bin/env python3
"""
Simple Samsung TV Pairing Script

Usage: python pair_tv.py <tv_id>
Returns: pair_success, pair_failed, or id_not_found
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


def save_token(tv_id, token):
    """Save token to tokens.json"""
    tokens_path = PROJECT_ROOT / "tokens.json"
    tokens = load_tokens()
    tokens[tv_id] = {
        "token": token,
        "paired_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(tokens_path, 'w') as file:
        json.dump(tokens, file, indent=2)


def find_tv(tv_id, tvs):
    """Find TV by ID"""
    for tv in tvs:
        if tv['id'] == tv_id:
            return tv
    return None


def pair_tv(tv):
    """Attempt to pair with TV"""
    try:
        samsung_tv = SamsungTVWS(
            host=tv['host'],
            port=tv['port'],
            name="Samsung TV Controller",
            timeout=30
        )
        
        samsung_tv.open()
        
        # Wait a moment for pairing
        time.sleep(2)
        
        # Test connection with a simple command
        samsung_tv.send_key("KEY_VOLUP")
        time.sleep(0.1)
        samsung_tv.send_key("KEY_VOLDOWN")
        
        # Save token if available
        if hasattr(samsung_tv, 'token') and samsung_tv.token:
            save_token(tv['id'], samsung_tv.token)
        else:
            save_token(tv['id'], "NO_TOKEN_REQUIRED")
        
        samsung_tv.close()
        return True
        
    except Exception:
        return False


def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("pair_failed")
        sys.exit(1)
    
    tv_id = sys.argv[1]
    tvs = load_tv_config()
    
    # Find TV
    tv = find_tv(tv_id, tvs)
    if not tv:
        print("id_not_found")
        sys.exit(1)
    
    # Attempt pairing
    if pair_tv(tv):
        print("pair_success")
    else:
        print("pair_failed")


if __name__ == "__main__":
    main()