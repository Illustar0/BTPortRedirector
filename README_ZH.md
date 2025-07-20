# BTPortRedirector

中文 | [English](README.md)

一个 Python 工具，用于实时动态更新 qBittorrent 的公告 IP 和端口。此工具设计用于与 NAT 穿透解决方案（如 Natter）配合使用，自动更新 qBittorrent 向 Tracker 报告的公网地址。

## 功能特性

- 实时更新 qBittorrent 的端口和 IP 地址
- 与 qBittorrent Web API 无缝集成
- 地址更改后自动重新公告种子
- 通过 TOML 配置文件进行配置
- 全面的日志记录和轮转
- 错误处理和优雅关闭

## 系统要求

- Python 3.12+
- 启用了 Web UI 的 qBittorrent
- 依赖项：`httpx`、`loguru`

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/Illustar0/BTPortRedirector
cd BTPortRedirector
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

或使用 uv：
```bash
uv sync
```

## 配置

1. 创建或修改 `src/config.toml`：
```toml
[Qbittorrent]
api_endpoint = "http://127.0.0.1:8080"
username = "your_username"
password = "your_password"
```

2. 启用 qBittorrent Web UI：
   - 打开 qBittorrent
   - 转到 工具 → 选项 → Web UI
   - 勾选 "Web 用户界面（远程控制）"
   - 设置用户名和密码
   - 记录端口（默认：8080）

## 使用方法

此脚本设计为由 NAT 穿透工具或脚本调用，使用以下参数：

```bash
python src/agent.py <协议> <内网IP> <内网端口> <公网IP> <公网端口>
```

### 示例：
```bash
python src/agent.py tcp 192.168.1.100 45000 203.0.113.1 45000
```

### 与 Natter 集成

将此添加到您的 Natter 配置中，当端口映射更改时自动更新 qBittorrent：

```bash
python3 natter.py -m nftables -U -p <Qbittorrent 端口> -e /path/to/BTPortRedirector/src/agent.py
```

## 工作原理

1. 脚本接收公网 IP 和端口信息作为命令行参数
2. 从 `config.toml` 加载 qBittorrent 配置
3. 使用 qBittorrent Web API 进行身份验证
4. 更新公告 IP 和端口设置
5. 强制重新公告所有种子
6. 记录操作结果

## API 参考

### QBittorrentClient 类

处理 qBittorrent API 交互的主要类：

- `login(username, password)` - 使用 qBittorrent 进行身份验证
- `get_preferences()` - 检索当前首选项
- `set_preferences(preferences)` - 更新多个首选项
- `reannounce(hashes)` - 强制种子重新公告
- `stop(hashes)` / `start(hashes)` - 控制种子状态
- `logout()` - 结束会话

## 日志记录

日志自动保存到 `agent.log`，具有以下特性：
- 10 MB 轮转大小
- 保留 10 个日志文件
- 彩色编码的控制台输出

## 错误处理

脚本处理各种错误情况：
- 缺失或无效的配置文件
- qBittorrent 连接失败
- 身份验证错误
- API 请求失败

## 许可证

此项目是开源的。详情请参阅 LICENSE 文件。

## 贡献

欢迎贡献！请随时提交问题和拉取请求。