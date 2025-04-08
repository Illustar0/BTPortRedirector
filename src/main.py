import asyncio
import os
import sys
import tomllib
from multiprocessing import Process, Value
from urllib.parse import urlparse, parse_qs

import uvicorn
from fastapi import FastAPI
from loguru import logger
from mitmproxy.http import HTTPFlow
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

CONFIG_PATH = os.path.abspath(os.path.dirname(__file__)) + os.sep + "config.toml"

try:
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
# 配置不存在就使用默认配置
except FileNotFoundError:
    config = {}

webApiBindPort = config.get("settings", {}).get("webApiBindPort", 8000)
mitmProxyBindPort = config.get("settings", {}).get("mitmProxyBindPort", 8080)

try:
    public_port = sys.argv[1]
except Exception as e:
    public_port = None
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

    def response(self, flow: HTTPFlow) -> None:
        # 修改响应
        logger.debug(flow.response.content)


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
    mitmproxy_process.start()
    return mitmproxy_process


def stop_mitmproxy(process: Process):
    """停止 mitmproxy"""
    if process:
        process.terminate()
        process.join()


@app.get("/portChanged")
async def port_change(new_port: int):
    global port_value
    port_value.value = new_port


if __name__ == "__main__":
    mitmproxy_process = start_mitmproxy("127.0.0.1", mitmProxyBindPort, port_value)
    logger.info("MitmProxy is running")
    logger.info(f"WebAPI is listening in 127.0.0.1:{webApiBindPort}")
    uvicorn.run(app, host="127.0.0.1", port=webApiBindPort, log_config=None)
