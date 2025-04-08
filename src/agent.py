import socket
import subprocess
import sys
import urllib.request
import urllib.parse
import tomllib

python_executable = sys.executable
protocol, private_ip, private_port, public_ip, public_port = sys.argv[1:6]

with open("config.toml", "rb") as file:
    config = tomllib.load(file)
webApiBindPort = config["settings"]["webApiBindPort"]


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
