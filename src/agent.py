#!/usr/bin/env python3
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

import httpx
from httpx import Response
from loguru import logger

logger.add("agent.log", rotation="10 MB", retention=10)

def load_config(file_path: str) -> dict[str, Any] | None:
    try:
        with open(file_path) as f:
            return tomllib.loads(f.read())
    except FileNotFoundError:
        logger.error(f"File {file_path} not found")
        return None
    except tomllib.TOMLDecodeError:
        logger.error(f"Toml decode error")
        return None
    except Exception as _e:
        logger.error(_e)
        return None


class QBittorrentClient:
    def __init__(self, api_endpoint: str) -> None:
        self._client = httpx.Client(base_url=api_endpoint)

    def close(self) -> None:
        """释放 HTTPX 连接池"""
        self._client.close()

    def login(self, username: str, password: str) -> Response:
        data = {"username": username, "password": password}
        response = self._client.post("/api/v2/auth/login", data=data)
        return response

    def get_preferences(self):
        response = self._client.get("/api/v2/app/preferences")
        return response

    def set_preference(self, key: str, value: Any) -> Response:
        data = {key: value}
        response = self._client.post("/api/v2/app/setPreferences", json=data)
        return response

    def set_preferences(self, preferences: dict[str, Any]) -> Response:
        response = self._client.post(
            "/api/v2/app/setPreferences", data={"json": json.dumps(preferences)}
        )
        return response

    def reannounce(self, hashes: list[str] | None = None) -> Response:
        if hashes is None:
            hashes = ["all"]
        param = {"hashes": "|".join(hashes)}
        response = self._client.post("/api/v2/torrents/reannounce", data=param)
        return response

    def stop(self, hashes: list[str] | None = None) -> Response:
        if hashes is None:
            hashes = ["all"]
        param = {"hashes": "|".join(hashes)}
        response = self._client.post("/api/v2/torrents/stop", data=param)
        return response

    def start(self, hashes: list[str] | None = None) -> Response:
        if hashes is None:
            hashes = ["all"]
        param = {"hashes": "|".join(hashes)}
        response = self._client.post("/api/v2/torrents/start", data=param)
        return response

    def logout(self) -> Response:
        response = self._client.get("/api/v2/auth/logout")
        return response


if __name__ == "__main__":
    # protocol, private_ip, private_port, public_ip, public_port = sys.argv[1:6]
    _, _, _, public_ip, public_port = sys.argv[1:6]

    logger.opt(colors=True).info(
        f"Public address change to <blue>{public_ip}:{public_port}</blue>",
    )
    config = load_config(str(Path(__file__).parent / "config.toml"))
    if config.get("Qbittorrent", {}).get("api_endpoint") is None:
        logger.error("api_endpoint not set")
        exit(1)
    client = QBittorrentClient(config["Qbittorrent"]["api_endpoint"])
    try:
        client.login(
            config["Qbittorrent"]["username"], config["Qbittorrent"]["password"]
        ).raise_for_status()
        client.set_preferences(
            {"announce_ip": public_ip, "announce_port": int(public_port)}
        ).raise_for_status()
        logger.opt(colors=True).success(
            f"Successfully change qbittorrent announce address to <blue>{public_ip}:{public_port}</blue>"
        )
        client.reannounce().raise_for_status()
        logger.success(f"Successfully reannounce all torrents")
    except Exception as e:
        logger.error(e)
    finally:
        client.close()
