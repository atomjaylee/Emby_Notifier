# Emby Telegram Architecture Redesign

## Goal

Refactor Emby Notifier into a focused, robust, ARM-oriented service that only supports Emby webhook events and Telegram notifications. Remove Jellyfin, WeChat Work, and Bark support from code and documentation so the runtime path is smaller, clearer, and easier to maintain.

## Scope

In scope:

- Package the application under `src/emby_notifier/` with clear module boundaries.
- Keep `main.py` as a compatibility entrypoint that delegates to the package.
- Support only Emby webhook payloads.
- Support only Telegram as the notification channel.
- Keep TMDB as required metadata source and TVDB as an optional helper for TV series matching.
- Keep episode aggregation for multiple episode events arriving close together.
- Keep Docker packaging and GitHub Actions, but build only `linux/arm64`.
- Add focused pytest coverage around configuration, Emby parsing, event processing, Telegram formatting, and episode aggregation behavior.

Out of scope:

- Jellyfin payload preprocessing or documentation.
- WeChat Work sender support.
- Bark sender support.
- Multi-platform Docker image builds.
- A generic plugin framework for notification channels.

## Architecture

The refactor will replace the current flat script layout with a package that separates startup, configuration, webhook serving, media processing, API clients, and notification formatting.

```text
src/emby_notifier/
  __init__.py
  app.py
  config.py
  constants.py
  logging.py
  server.py
  clients/
    telegram.py
    tmdb.py
    tvdb.py
  domain/
    events.py
    media.py
  services/
    episode_buffer.py
    media_enricher.py
    processor.py
  notifiers/
    telegram.py
  utils/
    datetime.py
    text.py
```

`app.py` coordinates startup. It loads configuration, validates external credentials, constructs clients and services, sends the welcome message, and starts the HTTP server.

`config.py` is the only module that reads environment variables directly. It returns a validated config object with defaults for log level, log export, log path, bind host, bind port, and episode buffer timeout.

`server.py` owns aiohttp setup. It accepts only JSON requests, pushes request bodies into an async queue, and keeps message processing outside the request path.

`domain/events.py` parses Emby webhook payloads into small domain objects. It rejects unsupported event types and unsupported media types with explicit outcomes instead of hidden exceptions.

`domain/media.py` defines the internal media-detail structures used by notifiers. This keeps Telegram formatting independent from raw Emby payload shape.

`services/media_enricher.py` resolves TMDB IDs, optionally uses TVDB when available, fetches movie or episode details, and produces media detail objects.

`services/episode_buffer.py` owns episode aggregation state, locking, timers, and flush logic. It can be tested without aiohttp or real network calls.

`services/processor.py` is the application use case. It receives raw webhook text, parses it, handles test events, enriches media, routes movies immediately, and routes episodes through the buffer.

`notifiers/telegram.py` builds Telegram message text and calls the Telegram client. The Telegram HTTP client remains a small wrapper around Telegram Bot API requests.

## Data Flow

1. Emby sends a webhook POST to `/`.
2. `server.py` validates `Content-Type: application/json` and enqueues the raw body.
3. A worker task passes each message to `Processor.process_raw_message`.
4. `events.py` parses the JSON and classifies the event.
5. For `system.notificationtest`, the processor sends a Telegram test message.
6. For `library.new` movie events, the processor enriches metadata and sends a Telegram media message immediately.
7. For `library.new` episode events, the processor enriches metadata and adds the episode to `EpisodeBuffer`.
8. When the episode buffer flushes, it sends either a single episode message or an aggregated season update.

## Configuration

Required environment variables:

- `TMDB_API_TOKEN`
- `TG_BOT_TOKEN`
- `TG_CHAT_ID`

Optional environment variables:

- `TVDB_API_KEY`
- `TMDB_IMAGE_DOMAIN`, default `https://image.tmdb.org`
- `LOG_LEVEL`, default `INFO`
- `LOG_EXPORT`, default `False`
- `LOG_PATH`, default `/var/tmp/emby_notifier_tg`
- `HOST`, default `0.0.0.0`
- `PORT`, default `8000`
- `EPISODE_BUFFER_TIMEOUT`, default `10`

Removed environment variables:

- `WECHAT_CORP_ID`
- `WECHAT_CORP_SECRET`
- `WECHAT_AGENT_ID`
- `WECHAT_USER_ID`
- `WECHAT_MSG_TYPE`
- `BARK_SERVER`
- `BARK_DEVICE_KEYS`

## Error Handling

External HTTP clients will use explicit timeouts and raise typed client errors with useful context. The processor catches per-message failures, logs stack traces, and continues consuming the queue.

Webhook requests return quickly after validation and enqueueing. Invalid content type returns `415 Unsupported Media Type`. Malformed JSON is logged by the processor without stopping the worker.

Unsupported Emby events are logged and skipped. Unsupported media types are logged and skipped. Test notifications are handled explicitly.

## Docker And CI

Docker packaging remains part of the project. The Dockerfile will copy the local source tree into the image instead of cloning the repository during image build.

The GitHub Actions workflow will keep Docker Buildx, but build only `linux/arm64`. The old multi-platform `linux/amd64,linux/arm64` build target will be removed.

`docker-compose.yml` will be updated to show only the supported Emby + Telegram environment variables.

## Testing

The refactor will add pytest tests before implementation changes.

Required test coverage:

- Configuration rejects missing required variables and accepts optional defaults.
- Emby movie and episode webhook payloads parse into expected domain events.
- Unsupported events and unsupported media types produce skip outcomes.
- Telegram notifier formats movie, single episode, aggregated episode, welcome, and test messages.
- Episode buffer flushes one episode as a single message and multiple episodes as an aggregated message.
- Processor handles test events, movie events, and episode events using fake clients and fake notifier objects.

Network clients will be isolated behind small classes so tests can use fakes and do not call TMDB, TVDB, or Telegram.

## Migration Notes

Top-level legacy modules will be removed or replaced by compatibility shims only where needed for startup. `main.py` stays as the user-facing entrypoint.

README will be rewritten around the simplified supported feature set: Emby Server webhook setup, Telegram Bot setup, environment variables, Docker run, docker-compose, and ARM image notes.

The old `dockerfile-aarch64` can be removed after the main Dockerfile becomes ARM-oriented and the workflow builds only `linux/arm64`.
