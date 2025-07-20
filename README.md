# BTPortRedirector

[中文](README_ZH.md) | English

A Python tool that dynamically updates qBittorrent's announce IP and port in real-time. This tool is designed to work with NAT traversal solutions like Natter to automatically update the public address that qBittorrent reports to trackers.

## Features

- Real-time port and IP address updates for qBittorrent
- Seamless integration with qBittorrent Web API
- Automatic torrent re-announcement after address changes
- Configurable through TOML configuration file
- Comprehensive logging with rotation
- Error handling and graceful shutdown

## Requirements

- Python 3.12+
- qBittorrent with Web UI enabled
- Dependencies: `httpx`, `loguru`

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd BTPortRedirector
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or using uv:
```bash
uv sync
```

## Configuration

1. Create or modify `src/config.toml`:
```toml
[Qbittorrent]
api_endpoint = "http://127.0.0.1:8080"
username = "your_username"
password = "your_password"
```

2. Enable qBittorrent Web UI:
   - Open qBittorrent
   - Go to Tools → Options → Web UI
   - Check "Web User Interface (Remote control)"
   - Set username and password
   - Note the port (default: 8080)

## Usage

The script is designed to be called by NAT traversal tools or scripts with the following arguments:

```bash
python src/agent.py <protocol> <private_ip> <private_port> <public_ip> <public_port>
```

### Example:
```bash
python src/agent.py tcp 192.168.1.100 45000 203.0.113.1 45000
```

### Integration with Natter

Add this to your Natter configuration to automatically update qBittorrent when the port mapping changes:

```bash
python3 natter.py -m nftables -U -p <Qbittorrent Port> -e /path/to/BTPortRedirector/src/agent.py
```

## How It Works

1. The script receives public IP and port information as command line arguments
2. Loads qBittorrent configuration from `config.toml`
3. Authenticates with qBittorrent Web API
4. Updates the announce IP and port settings
5. Forces re-announcement of all torrents
6. Logs the operation results

## API Reference

### QBittorrentClient Class

The main class that handles qBittorrent API interactions:

- `login(username, password)` - Authenticate with qBittorrent
- `get_preferences()` - Retrieve current preferences
- `set_preferences(preferences)` - Update multiple preferences
- `reannounce(hashes)` - Force torrent re-announcement
- `stop(hashes)` / `start(hashes)` - Control torrent state
- `logout()` - End the session

## Logging

Logs are automatically saved to `agent.log` with:
- 10 MB rotation size
- 10 log file retention
- Color-coded console output

## Error Handling

The script handles various error conditions:
- Missing or invalid configuration files
- qBittorrent connection failures
- Authentication errors
- API request failures

## License

This project is open source. See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.