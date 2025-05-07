#!/usr/bin/env python3
import http.client
import json
import os
import socket
import subprocess
import sys
import tomllib
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie

# 常量
QBITTORRENT_51 = False
QBITTORRENT_USERNAME = "admin"
QBITTORRENT_PASSWORD = "admin"
QBITTORRENT_API_ENDPOINT = "http://127.0.0.1:8080"
BYPASS_AUTH = False
RESTART_COMMAND = "systemctl restart qbittorrent-nox"

CONFIG_PATH = os.path.abspath(os.path.dirname(__file__)) + os.sep + "config.toml"

python_executable = sys.executable
protocol, private_ip, private_port, public_ip, public_port = sys.argv[1:6]


if QBITTORRENT_51:
    url_parts = urllib.parse.urlparse(QBITTORRENT_API_ENDPOINT)
    host = url_parts.netloc
    base_path = url_parts.path

    # Determine if using HTTPS
    is_https = url_parts.scheme == "https"

    # Create connection
    if is_https:
        conn = http.client.HTTPSConnection(host)
    else:
        conn = http.client.HTTPConnection(host)

    cookies = {}

    # Handle authentication if needed
    if not BYPASS_AUTH:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        auth_data = urllib.parse.urlencode(
            {"username": QBITTORRENT_USERNAME, "password": QBITTORRENT_PASSWORD}
        )

        conn.request(
            "POST", f"{base_path}/api/v2/auth/login", body=auth_data, headers=headers
        )
        auth_response = conn.getresponse()

        # Extract cookies from response
        if "set-cookie" in auth_response.headers:
            cookie = SimpleCookie()
            cookie.load(auth_response.headers["set-cookie"])
            for key, morsel in cookie.items():
                cookies[key] = morsel.value

        # Read and discard the response body
        auth_response.read()

    # Prepare cookie header for subsequent requests
    cookie_header = "; ".join([f"{key}={value}" for key, value in cookies.items()])
    headers = {"Cookie": cookie_header} if cookie_header else {}

    # Get current preferences
    conn.request("GET", f"{base_path}/api/v2/app/preferences", headers=headers)
    pref_response = conn.getresponse()
    if pref_response.status != 200:
        raise Exception(
            f"Failed to get preferences: {pref_response.status} {pref_response.reason}"
        )

    response_data = pref_response.read().decode("utf-8")
    response_json = json.loads(response_data)

    # Update preferences with new IP and port
    response_json["announce_ip"] = str(public_ip)
    response_json["announce_port"] = int(public_port)

    # Set updated preferences
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    set_pref_data = urllib.parse.urlencode({"json": json.dumps(response_json)})

    conn.request(
        "POST",
        f"{base_path}/api/v2/app/setPreferences",
        body=set_pref_data,
        headers=headers,
    )
    set_response = conn.getresponse()
    if set_response.status != 200:
        raise Exception(
            f"Failed to set preferences: {set_response.status} {set_response.reason}"
        )

    # Read and discard the response body
    set_response.read()

    # Close connection
    conn.close()

    # Restart qBittorrent
    subprocess.Popen(RESTART_COMMAND, shell=True)
else:
    try:
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
    # 配置不存在就使用默认配置
    except FileNotFoundError:
        config = {}

    webApiBindPort = config.get("settings", {}).get("webApiBindPort", 8000)

    def is_running(port: int):
        """检查程序是否已经在运行"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                # 尝试连接到端口，如果连接成功，说明程序已经在运行
                s.connect(("127.0.0.1", port))
                return True
            except ConnectionRefusedError:
                # 如果连接失败，说明程序没有在运行
                return False

    if is_running(webApiBindPort):
        url = f"http://127.0.0.1:{webApiBindPort}/portChanged"
        params = {"new_port": public_port}
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        urllib.request.urlopen(full_url)
    else:
        subprocess.Popen(
            [python_executable, "main.py", str(webApiBindPort)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
