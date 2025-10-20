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
import base64
import ssl
import time
import urllib.request
import urllib.error
import socket
from typing import Optional, Callable

try:
    import websocket  # from websocket-client (pulled in by samsungtvws)
except ImportError:
    websocket = None
    
PROJECT_ROOT = Path(__file__).parent.parent

def get_comprehensive_tv_info(tv):
    """Get comprehensive TV info including current display status"""
    tokens = load_tokens()
    token_data = tokens.get(tv['id'], {})
    token = token_data.get('token') if token_data else None
    
    if not token:
        return "no_token"
    
    client_name = "ComprehensiveInfoQuery"

    # Quick online check to avoid long WS timeouts when TV is off
    if not is_tv_online(tv['host']):
        return "tv_offline"
    samsung_tv = SamsungTVWS(
        host=tv['host'],
        port=tv.get('port', 8002),
        name=client_name,
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
            "port": tv.get('port', 8002)
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
        
        # 2. Available applications via raw WebSocket
        print("\033[93mAvailable Apps (via raw WebSocket):\033[0m")
        apps = get_available_apps_raw_ws(
            tv['host'],
            tv.get('port', 8002),
            token,
            client_name=client_name,
            on_new_token=on_new_token,
            timeout=8.0,
        )
        if apps:
            tv_info["available_apps"] = apps
            print(json.dumps(apps, indent=2))
        else:
            tv_info["available_apps_error"] = "timeout_or_not_supported"
            print(f"\033[91mError: timeout_or_not_supported\033[0m")
        
        # 3. Try to get current input via raw WebSocket (no samsungtvws helpers)
        print("\033[94mCurrent Input (via raw WebSocket):\033[0m")
        def on_new_token(new_token: str):
            if new_token and new_token != token:
                persist_token_update(tv['id'], new_token)

        current_input = get_current_input_raw_ws(
            tv['host'],
            tv.get('port', 8002),
            token,
            client_name=client_name,
            on_new_token=on_new_token
        )
        if not current_input:
            # 4. Fallback to REST app/status probing for common inputs
            print("\033[93mRaw WebSocket did not yield current input, trying REST fallback...\033[0m")
            current_input = get_current_input_via_rest(tv['host'])
        
        if current_input:
            tv_info["current_input"] = current_input
            print(json.dumps({"current_input": current_input}, indent=2))
        else:
            tv_info["current_input"] = "unknown"
            print("\033[91mCurrent Input: Unable to determine via WS/REST\033[0m")
        
        samsung_tv.close()
        return json.dumps(tv_info, indent=2)
        
    except Exception as e:
        try:
            samsung_tv.close()
        except:
            pass
        return f"websocket_error: {e}"


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

def persist_token_update(tv_id: str, new_token: str) -> None:
    """Persist an updated token to tokens.json in-place.
    Schema expectation: tokens.json is a dict keyed by tv id, with {'token': '...'} inside.
    """
    tokens_path = PROJECT_ROOT / "tokens.json"
    tokens = {}
    try:
        with open(tokens_path, 'r') as file:
            tokens = json.load(file)
    except Exception:
        tokens = {}

    # Merge update
    entry = tokens.get(tv_id, {})
    entry['token'] = new_token
    tokens[tv_id] = entry

    # Write back atomically-ish
    tmp_path = tokens_path.with_suffix('.json.tmp')
    try:
        with open(tmp_path, 'w') as file:
            json.dump(tokens, file, indent=2)
        # Replace
        Path(tmp_path).replace(tokens_path)
    except Exception:
        # Fallback to direct write
        with open(tokens_path, 'w') as file:
            json.dump(tokens, file, indent=2)

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

def get_current_input_raw_ws(
    host: str,
    port: int,
    token: str,
    timeout: float = 5.0,
    client_name: str = "InputQuery",
    on_new_token: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Connect directly to the Samsung remote-control WebSocket and try to detect the running app.
    If the running app corresponds to an input (e.g., org.tizen.tv.input-HDMI1), return that input.
    Returns a short string like "HDMI1", "TV", or "app:<AppName>" when not an external input.
    """
    if websocket is None:
        return None

    # Build WS URL
    # Channel: samsung.remote.control
    # Name must be base64
    name_b64 = base64.b64encode(client_name.encode("utf-8")).decode("utf-8")
    url = f"wss://{host}:{port}/api/v2/channels/samsung.remote.control?name={name_b64}"

    ws = None
    try:
        ws = websocket.create_connection(
            url,
            timeout=timeout,
            sslopt={"cert_reqs": ssl.CERT_NONE}
        )

        # Complete connect handshake
        connect_msg = {
            "method": "ms.channel.connect",
            "params": {"client_name": client_name, "token": token}
        }
        ws.send(json.dumps(connect_msg))

        # Try to read the connect ack (capture a new token if TV provides it)
        try:
            ws.settimeout(2.0)
            raw_ack = ws.recv()
            try:
                ack = json.loads(raw_ack)
                if isinstance(ack, dict):
                    # If TV immediately indicates timeout, don't proceed
                    if ack.get("event") == "ms.channel.timeOut":
                        return None
                    data_part = ack.get("data")
                    if isinstance(data_part, dict):
                        new_token = data_part.get("token") or data_part.get("client_key") or data_part.get("auth_token")
                        if new_token and on_new_token:
                            on_new_token(new_token)
            except Exception:
                pass
        except Exception:
            pass

        # Candidate events observed across Tizen firmwares that may return the foreground app
        events_to_try = [
            "ed.apps.getForegroundApp",
            "ed.launcher.get_running_app",
            "ed.launcher.app.getRunningApp",
            "ed.getRunningApp",
            "ed.installedApp.getRunning",
            "ed.apps.getRunning",
        ]

        # Send events
        for ev in events_to_try:
            msg = {"method": "ms.channel.emit", "params": {"event": ev, "to": "host"}}
            try:
                ws.send(json.dumps(msg))
            except Exception:
                continue

        # Listen briefly for any response that contains a running/foreground app
        ws.settimeout(timeout)
        end = time.time() + timeout
        while time.time() < end:
            try:
                raw = ws.recv()
            except (websocket.WebSocketTimeoutException, socket.timeout):
                break
            except Exception:
                break

            try:
                data = json.loads(raw)
            except Exception:
                continue

            # Heuristics: find appId/id/name in response payloads
            app_info = None
            # Common places: data (dict), data.data, params.data depending on firmware
            candidates = []
            if isinstance(data, dict):
                candidates.append(data.get("data"))
                if "params" in data and isinstance(data["params"], dict):
                    candidates.append(data["params"].get("data"))
                # Some firmwares use distinct keys for foreground/running app
                candidates.append(data.get("foregroundApp"))
                candidates.append(data.get("runningApp"))

            for cand in candidates:
                if isinstance(cand, dict):
                    app_info = cand
                    # Some responses nest as {"appId": "...", "name": "..."} or {"id": "...", "name": "..."}
                    app_id = app_info.get("appId") or app_info.get("id")
                    app_name = app_info.get("name") or app_info.get("app_name")
                    if app_id:
                        # Inputs typically look like org.tizen.tv.input-<INPUT>
                        if app_id.startswith("org.tizen.tv.input-"):
                            return app_id.split("org.tizen.tv.input-")[-1]
                        # Not an input, but still useful
                        return f"app:{app_name or app_id}"

                # Some TVs respond with a list of running apps
                if isinstance(cand, list):
                    for item in cand:
                        if not isinstance(item, dict):
                            continue
                        app_id = item.get("appId") or item.get("id")
                        app_name = item.get("name") or item.get("app_name")
                        running = item.get("running") or item.get("visible") or (item.get("status") == "running")
                        if running and app_id:
                            if app_id.startswith("org.tizen.tv.input-"):
                                return app_id.split("org.tizen.tv.input-")[-1]
                            return f"app:{app_name or app_id}"

        return None
    except Exception:
        return None
    finally:
        try:
            if ws:
                ws.close()
        except Exception:
            pass

def get_current_input_via_rest(host: str, timeout: float = 4.0) -> str:
    """
    Fallback method using REST: check status of common input appIds at /api/v2/app/status/{appId}.
    Returns first running/visible input or None.
    """
    # Common input app IDs seen across models/firmwares
    input_app_ids = [
        "org.tizen.tv.input-TV",
        "org.tizen.tv.input-HDMI1",
        "org.tizen.tv.input-HDMI2",
        "org.tizen.tv.input-HDMI3",
        "org.tizen.tv.input-HDMI4",
        "org.tizen.tv.input-AV",
        "org.tizen.tv.input-Component",
    ]

    for app_id in input_app_ids:
        url = f"http://{host}:8001/api/v2/app/status/{app_id}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                # Some firmwares use 'running', others 'visible' or a 'status' field
                if payload.get("running") or payload.get("visible") or payload.get("status") == "running":
                    # Return the input suffix (e.g., HDMI1)
                    if app_id.startswith("org.tizen.tv.input-"):
                        return app_id.split("org.tizen.tv.input-")[-1]
                    return "TV"
        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, ValueError):
            continue

    return None

def is_tv_online(host: str, timeout: float = 1.5) -> bool:
    """Fast probe to check if TV REST API is reachable on port 8001."""
    url = f"http://{host}:8001/api/v2/"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def get_available_apps_raw_ws(
    host: str,
    port: int,
    token: str,
    timeout: float = 8.0,
    client_name: str = "InputQuery",
    on_new_token: Optional[Callable[[str], None]] = None,
) -> list:
    """
    Query installed/available apps via the remote-control WebSocket by emitting several
    app-list events and aggregating responses.
    Returns a list of {appId, name} (best-effort) or [] if not available.
    """
    if websocket is None:
        return []

    name_b64 = base64.b64encode(client_name.encode("utf-8")).decode("utf-8")
    url = f"wss://{host}:{port}/api/v2/channels/samsung.remote.control?name={name_b64}"

    ws = None
    try:
        ws = websocket.create_connection(
            url,
            timeout=timeout,
            sslopt={"cert_reqs": ssl.CERT_NONE}
        )

        connect_msg = {
            "method": "ms.channel.connect",
            "params": {"client_name": client_name, "token": token}
        }
        ws.send(json.dumps(connect_msg))

        # Try to capture updated token
        try:
            ws.settimeout(2.0)
            raw_ack = ws.recv()
            try:
                ack = json.loads(raw_ack)
                if isinstance(ack, dict):
                    data_part = ack.get("data")
                    if isinstance(data_part, dict):
                        new_token = data_part.get("token") or data_part.get("client_key") or data_part.get("auth_token")
                        if new_token and on_new_token:
                            on_new_token(new_token)
            except Exception:
                pass
        except Exception:
            pass

        # Candidate events for app listing across firmwares
        events_to_try = [
            "ed.installedApp.get",
            "ed.installedApp.getList",
            "ed.apps.getList",
            "ed.apps.getInstalled",
            "ed.launcher.get_app_list",
        ]

        for ev in events_to_try:
            msg = {"method": "ms.channel.emit", "params": {"event": ev, "to": "host"}}
            try:
                ws.send(json.dumps(msg))
            except Exception:
                continue

        ws.settimeout(timeout)
        end = time.time() + timeout
        apps_map = {}
        while time.time() < end:
            try:
                raw = ws.recv()
            except (websocket.WebSocketTimeoutException, socket.timeout):
                break
            except Exception:
                break

            try:
                data = json.loads(raw)
            except Exception:
                continue

            # Collect any list-like payloads from common locations
            lists = []
            if isinstance(data, dict):
                for key in ("data", "apps", "installedApps", "installed", "list"):
                    val = data.get(key)
                    if isinstance(val, list):
                        lists.append(val)
                if "params" in data and isinstance(data["params"], dict):
                    pdata = data["params"].get("data")
                    if isinstance(pdata, list):
                        lists.append(pdata)

            for lst in lists:
                for item in lst:
                    if not isinstance(item, dict):
                        continue
                    app_id = item.get("appId") or item.get("id") or item.get("appid")
                    name = item.get("name") or item.get("app_name") or item.get("title")
                    if not app_id and not name:
                        continue
                    key = app_id or name
                    # Normalize shape
                    apps_map[key] = {"appId": app_id or key, "name": name or (app_id or key)}

        return list(apps_map.values())
    except Exception:
        return []
    finally:
        try:
            if ws:
                ws.close()
        except Exception:
            pass

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
    print(result)

if __name__ == "__main__":
    main()