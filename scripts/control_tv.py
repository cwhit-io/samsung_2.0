#!/usr/bin/env python3
"""
Samsung TV Control Script

Usage: python control_tv.py <tv_id> <command>
Returns: control_success, control_failed, id_not_found, no_token, or connection_failed
"""

import json
import sys
import time
import threading
from pathlib import Path
from samsungtvws import SamsungTVWS

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

def safe_control_with_timeout(func, timeout_seconds=8):
    """Execute control function with timeout protection"""
    result = {}
    exception = {}
    
    def target():
        try:
            result['success'] = func()
        except Exception as e:
            exception['error'] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        return False, "timeout"
    
    if 'error' in exception:
        return False, str(exception['error'])
    
    return result.get('success', False), None

def validate_key_command(command):
    """Validate if command is a proper Samsung TV key"""
    # Common Samsung TV keys
    valid_keys = [
        # Power
        "KEY_POWER", "KEY_POWEROFF",
        # Volume
        "KEY_VOLUP", "KEY_VOLDOWN", "KEY_MUTE",
        # Channels
        "KEY_CHUP", "KEY_CHDOWN",
        # Navigation
        "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", 
        "KEY_ENTER", "KEY_RETURN",
        # Menu
        "KEY_MENU", "KEY_HOME", "KEY_GUIDE", "KEY_INFO",
        # Numbers
        "KEY_0", "KEY_1", "KEY_2", "KEY_3", "KEY_4",
        "KEY_5", "KEY_6", "KEY_7", "KEY_8", "KEY_9",
        # Apps
        "KEY_NETFLIX", "KEY_AMAZON", "KEY_APPS",
        # Media
        "KEY_PLAY", "KEY_PAUSE", "KEY_STOP", "KEY_REWIND", "KEY_FF"
    ]
    
    # Allow any KEY_ command or validate against known keys
    return command.startswith("KEY_") or command in valid_keys

def control_tv(tv, command):
    """Send control command to TV"""
    def execute_control():
        # Load token - required for control commands
        tokens = load_tokens()
        token_data = tokens.get(tv['id'], {})
        token = token_data.get('token') if token_data else None
        
        if not token:
            raise Exception("no_token_available")
        
        # Validate command
        if not validate_key_command(command):
            raise Exception(f"invalid_key_command: {command}")
        
        # Create TV connection
        samsung_tv = SamsungTVWS(
            host=tv['host'],
            port=tv.get('port', 8002),
            name="TV_Controller",
            token=token,
            timeout=5
        )
        
        try:
            # Open connection (this was missing!)
            samsung_tv.open()
            
            # Send the key command
            samsung_tv.send_key(command)
            
            # Small delay to ensure command is processed
            time.sleep(0.2)
            
            # Close connection
            samsung_tv.close()
            
            return True
            
        except Exception as e:
            # Ensure connection is closed even on error
            try:
                samsung_tv.close()
            except:
                pass
            raise e
    
    # Execute with timeout protection
    success, error = safe_control_with_timeout(execute_control, timeout_seconds=8)
    
    if not success:
        if error == "timeout":
            return False, "connection_timeout"
        elif "no_token_available" in str(error):
            return False, "no_token"
        elif "invalid_key_command" in str(error):
            return False, "invalid_command"
        else:
            return False, "connection_failed"
    
    return True, "success"

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
    success, status = control_tv(tv, command)
    
    if success:
        print("control_success")
    else:
        # Return specific error status
        if status == "no_token":
            print("no_token")
        elif status == "invalid_command":
            print("invalid_command")
        elif status == "connection_timeout":
            print("connection_timeout")
        else:
            print("control_failed")

if __name__ == "__main__":
    main()