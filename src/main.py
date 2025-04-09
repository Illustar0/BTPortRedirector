import asyncio
import os
import signal
import sys
import tomllib
from multiprocessing import Process, Value
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs

import uvicorn
from fastapi import FastAPI, HTTPException
from loguru import logger
from mitmproxy.http import HTTPFlow
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

CONFIG_PATH = os.path.abspath(os.path.dirname(__file__)) + os.sep + "config.toml"


# 加载配置
def load_config():
    try:
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    # 配置不存在就使用默认配置
    except FileNotFoundError:
        return {}


config = load_config()
webApiBindPort = config.get("settings", {}).get("webApiBindPort", 8000)
mitmProxyBindPort = config.get("settings", {}).get("mitmProxyBindPort", 8080)

app = FastAPI()

# 使用共享内存来存储端口信息
port_value = Value("i", 25565)  # 初始值设为默认端口


class Addon:
    def __init__(self, port_value):
        self.port_value = port_value

    def request(self, flow: HTTPFlow):
        # 检查是否是BitTorrent tracker announce请求
        if (
            "peer_id" in flow.request.url
            and "info_hash" in flow.request.url
            and "port" in flow.request.url
        ):
            # 解析URL和查询参数
            host_header = flow.request.host_header
            parsed_url = urlparse(flow.request.url)
            query_params = parse_qs(parsed_url.query)

            # 修改端口值
            if "port" in query_params:
                new_port = self.port_value.value
                logger.debug(
                    f"Detected port: {query_params['port'][0]},change to {new_port}"
                )
                url = flow.request.url
                lo = url.replace(f"port={query_params['port'][0]}", f"port={new_port}")
                flow.request.url = lo
                flow.request.host_header = host_header


async def config_mitmproxy(listen_host="127.0.0.1", listen_port=8080, port_value=None):
    """配置 mitmproxy 参数与启动"""
    options = Options(
        listen_host=listen_host,
        listen_port=listen_port,
        ssl_insecure=True,
    )
    script = Addon(port_value)
    addons = [script]

    # 创建 DumpMaster 实例
    master = DumpMaster(options)
    master.addons.add(*addons)
    try:
        await master.run()  # 启动 mitmproxy 主循环
    except KeyboardInterrupt:
        master.shutdown()  # 当手动中断时，关闭 master


def run_mitmproxy(listen_host: str, listen_port: int, port_value):
    """运行 mitmproxy"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(config_mitmproxy(listen_host, listen_port, port_value))
    loop.close()


def start_mitmproxy(listen_host: str, listen_port: int, port_value) -> Process:
    """启动 mitmproxy"""
    mitmproxy_process = Process(
        target=run_mitmproxy, args=(listen_host, listen_port, port_value)
    )
    mitmproxy_process.daemon = True
    mitmproxy_process.start()
    return mitmproxy_process


def stop_mitmproxy(process: Process):
    """停止 mitmproxy"""
    if process:
        process.terminate()
        process.join()


@app.get("/portChanged")
async def port_change(new_port: int) -> Dict[str, Any]:
    """更改重定向的目标端口"""
    if not 1 <= new_port <= 65535:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid port: {new_port}, the port must be between 1-65535",
        )

    global port_value
    port_value.value = new_port
    logger.info(f"Port switched to {new_port}")
    return {"status": "success", "message": f"Port switched to {new_port}"}


@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """获取当前状态"""
    return {
        "currentPort": port_value.value,
        "mitmproxyPort": mitmProxyBindPort,
        "apiPort": webApiBindPort,
    }


def handle_exit(signum, frame) -> None:
    """处理退出信号"""
    logger.info(f"Received signal {signum}, ready to exit.")
    sys.exit(0)


# 注册信号处理器
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)


def init_port_value():
    try:
        port_value.value = int(sys.argv[1])
    except IndexError:
        logger.warning("No port parameter provided.")
    except ValueError as e:
        logger.error(f"Invalid port: {e}")


if __name__ == "__main__":
    # 初始化端口值
    init_port_value()

    try:
        mitmproxy_process = start_mitmproxy("127.0.0.1", mitmProxyBindPort, port_value)
        logger.info("MitmProxy is running")
        logger.info(f"WebAPI is listening in 127.0.0.1:{webApiBindPort}")
        uvicorn.run(app, host="127.0.0.1", port=webApiBindPort, log_config=None)
    except Exception as e:
        logger.error(f"Program startup failed: {e}")
    finally:
        if "mitmproxy_process" in locals():
            stop_mitmproxy(mitmproxy_process)
