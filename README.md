# Emby Notifier

Emby Notifier 是一个基于 Emby Server Webhooks 的媒体入库通知服务。它接收 Emby 的新媒体事件，使用 TMDB 补全影片或剧集详情，然后通过 Telegram Bot 推送到指定聊天或频道。

当前版本只保留：

- Emby Server webhook
- Telegram Bot 通知
- TMDB 元数据检索
- 可选 TVDB 辅助剧集匹配
- ARM64 Docker 镜像构建

已移除 Jellyfin、企业微信和 Bark 支持，以减少运行路径和配置分支。

## 版本要求

建议使用 **Emby Server 4.8.0.80 或更新版本**。

本项目基于 Emby Server 的 Webhooks/通知能力工作。旧版 Emby 可能需要 Emby Premiere 才能使用 Webhooks。

## 环境变量

服务默认监听 `0.0.0.0:8000`。

| 参数 | 要求 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `TMDB_API_TOKEN` | 必须 | 无 | TMDB API Read Access Token |
| `TG_BOT_TOKEN` | 必须 | 无 | Telegram Bot Token |
| `TG_CHAT_ID` | 必须 | 无 | Telegram chat/channel ID |
| `TVDB_API_KEY` | 可选 | 无 | TVDB API Key，用于部分剧集 TMDB 匹配 |
| `TMDB_IMAGE_DOMAIN` | 可选 | `https://image.tmdb.org` | TMDB 图片域名，可替换为代理域名 |
| `LOG_LEVEL` | 可选 | `INFO` | 日志等级：`DEBUG`、`INFO`、`WARNING` |
| `LOG_EXPORT` | 可选 | `False` | 是否输出日志文件 |
| `LOG_PATH` | 可选 | `/var/tmp/emby_notifier_tg` | 日志文件目录 |
| `HOST` | 可选 | `0.0.0.0` | HTTP 服务监听地址 |
| `PORT` | 可选 | `8000` | HTTP 服务监听端口 |
| `EPISODE_BUFFER_TIMEOUT` | 可选 | `10` | 剧集聚合等待秒数 |
| `REQUEST_TIMEOUT` | 可选 | `8` | 外部 API 请求超时时间 |

## Docker Run

```bash
docker run -d --name=emby-notifier-tg --restart=unless-stopped \
  -e TMDB_API_TOKEN=Your_TMDB_API_Token \
  -e TG_BOT_TOKEN=Your_Telegram_Bot_Token \
  -e TG_CHAT_ID=Your_Telegram_Chat_ID \
  -e TVDB_API_KEY=Your_TVDB_API_Key \
  -p 8000:8000 \
  b1gfac3c4t/emby_notifier_tg:latest
```

## Docker Compose

```yaml
version: '3'
services:
  emby_notifier_tg:
    build:
      context: .
      dockerfile: dockerfile
    image: b1gfac3c4t/emby_notifier_tg:latest
    environment:
      - TZ=Asia/Shanghai
      - TMDB_API_TOKEN=<Your TMDB API Token>
      - TG_BOT_TOKEN=<Your Telegram Bot Token>
      - TG_CHAT_ID=<Your Telegram Chat ID>
      - TVDB_API_KEY=<Your TVDB API Key>
      - LOG_LEVEL=INFO
      - LOG_EXPORT=False
      - LOG_PATH=/var/tmp/emby_notifier_tg/
    network_mode: "bridge"
    ports:
      - "8000:8000"
    restart: unless-stopped
```

启动：

```bash
docker-compose up -d
```

## ARM 镜像

项目的 Dockerfile 使用 ARM64 Python 基础镜像，GitHub Actions 只构建 `linux/arm64`。

本地构建：

```bash
docker buildx build --platform linux/arm64 -f dockerfile -t emby-notifier:arm64-test --load .
```

## Emby Server 设置

1. 打开 Emby Server 控制台，进入 “设置” -> “通知”。
2. 添加 Webhooks 通知。
3. URL 填写 Notifier 地址，例如 `http://192.168.1.100:8000`。
4. 数据类型选择 `application/json`。
5. 发送测试通知，确认 Telegram 能收到测试消息。
6. 勾选媒体库的新媒体添加事件并保存。

参考截图仍保留在 `doc/` 目录中。

## 行为说明

- 只处理 `library.new` 媒体新增事件。
- 只支持 `Movie` 和 `Episode`。
- `system.notificationtest` 会发送 Telegram 测试消息。
- Emby 消息没有 Server URL 时默认使用 `https://emby.media`。
- 多个剧集事件在 `EPISODE_BUFFER_TIMEOUT` 时间窗口内到达时，会合并为一条剧集更新通知。
- 单条消息处理失败不会终止队列 worker。

## 本地开发

运行测试：

```bash
PYTHONPATH=src pytest -v
```

语法检查：

```bash
python -m compileall src main.py
```

## 局限性

Emby Server 的新媒体事件触发取决于媒体库扫描和文件监控机制。如果 Emby 没有触发 webhook，本服务不会主动扫描媒体库。

当 Emby 事件缺少 TMDB/TVDB provider id 时，服务会使用 TMDB 搜索结果进行匹配；少数媒体可能出现匹配不准确。

## 参考文档

- [TMDB API 文档](https://developers.themoviedb.org/3)
- [Telegram Bot API 文档](https://core.telegram.org/bots/api)
