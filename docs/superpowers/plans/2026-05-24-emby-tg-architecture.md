# Emby TG Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the service as an Emby-only, Telegram-only, ARM-only Python package with clearer boundaries, stronger tests, and simpler runtime behavior.

**Architecture:** Move code into `src/emby_notifier/`, isolate environment configuration, parse Emby webhook events into domain objects, enrich media through TMDB/TVDB clients, and send all notifications through a single Telegram notifier. Keep HTTP request handling asynchronous and push media work into a processor service with per-message error isolation.

**Tech Stack:** Python 3.11, aiohttp, requests, colorlog, pytest, Docker Buildx.

---

## File Map

- Create `pyproject.toml`: package metadata, runtime dependencies, pytest config.
- Create `src/emby_notifier/__init__.py`: package version export.
- Create `src/emby_notifier/constants.py`: app metadata and welcome payload.
- Create `src/emby_notifier/config.py`: env loading and validation.
- Create `src/emby_notifier/logging.py`: logger setup with optional file export.
- Create `src/emby_notifier/app.py`: startup composition and async entrypoint.
- Create `src/emby_notifier/server.py`: aiohttp server and queue worker.
- Create `src/emby_notifier/utils/datetime.py`: Emby date parsing helpers.
- Create `src/emby_notifier/utils/text.py`: Telegram Markdown escaping.
- Create `src/emby_notifier/domain/events.py`: Emby webhook parser and event dataclasses.
- Create `src/emby_notifier/domain/media.py`: media detail dataclasses.
- Create `src/emby_notifier/clients/tmdb.py`: TMDB client with timeout and typed errors.
- Create `src/emby_notifier/clients/tvdb.py`: optional TVDB client with timeout and typed errors.
- Create `src/emby_notifier/clients/telegram.py`: Telegram Bot API client.
- Create `src/emby_notifier/notifiers/telegram.py`: Telegram message formatting and sending.
- Create `src/emby_notifier/services/media_enricher.py`: TMDB/TVDB orchestration.
- Create `src/emby_notifier/services/episode_buffer.py`: aggregation buffer.
- Create `src/emby_notifier/services/processor.py`: raw webhook processing use case.
- Replace `main.py`: compatibility entrypoint calling `emby_notifier.app.main`.
- Delete `bark.py`, `wxapp.py`, `sender.py`, `media.py`, `tmdb_api.py`, `tvdb_api.py`, `tgbot.py`, `my_httpd.py`, `my_utils.py`, and `log.py` after equivalent package modules are green.
- Modify `dockerfile`: ARM-oriented image that copies local source and installs package.
- Delete `dockerfile-aarch64`: redundant after ARM-only Dockerfile.
- Modify `.github/workflows/docker-image.yml`: build only `linux/arm64`.
- Modify `docker-compose.yml`: only Emby/TG/TMDB/TVDB env vars.
- Rewrite `README.md`: simplified Emby + Telegram instructions.

## Task 1: Test Harness And Package Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/emby_notifier/__init__.py`
- Create: `src/emby_notifier/constants.py`
- Create: `src/emby_notifier/config.py`
- Test: `tests/test_config.py`
- Modify: `main.py`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_config.py`:

```python
import pytest

from emby_notifier.config import ConfigError, load_config


def test_load_config_requires_tmdb_and_telegram(monkeypatch):
    monkeypatch.delenv("TMDB_API_TOKEN", raising=False)
    monkeypatch.delenv("TG_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TG_CHAT_ID", raising=False)

    with pytest.raises(ConfigError) as exc:
        load_config()

    message = str(exc.value)
    assert "TMDB_API_TOKEN" in message
    assert "TG_BOT_TOKEN" in message
    assert "TG_CHAT_ID" in message


def test_load_config_uses_defaults(monkeypatch):
    monkeypatch.setenv("TMDB_API_TOKEN", "tmdb-token")
    monkeypatch.setenv("TG_BOT_TOKEN", "tg-token")
    monkeypatch.setenv("TG_CHAT_ID", "-100123")
    monkeypatch.delenv("TVDB_API_KEY", raising=False)
    monkeypatch.delenv("TMDB_IMAGE_DOMAIN", raising=False)
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("EPISODE_BUFFER_TIMEOUT", raising=False)

    config = load_config()

    assert config.tmdb_api_token == "tmdb-token"
    assert config.telegram_bot_token == "tg-token"
    assert config.telegram_chat_id == "-100123"
    assert config.tvdb_api_key is None
    assert config.tmdb_image_domain == "https://image.tmdb.org"
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.episode_buffer_timeout == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_config.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'emby_notifier'`.

- [ ] **Step 3: Add package metadata and config implementation**

Create `pyproject.toml`:

```toml
[project]
name = "emby-notifier"
version = "4.2.0"
requires-python = ">=3.11"
dependencies = [
  "aiohttp>=3.9",
  "colorlog>=6.8",
  "requests>=2.31",
]

[project.optional-dependencies]
test = [
  "pytest>=8.0",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `src/emby_notifier/__init__.py`:

```python
__version__ = "4.2.0"
```

Create `src/emby_notifier/constants.py`:

```python
APP_NAME = "Emby Notifier"
AUTHOR = "xu4n_ch3n"
VERSION = "4.2.0"
UPDATE_TIME = "2026-05-24"
DESCRIPTION = "Emby-only media notification service for Telegram."
REPOSITORY = "https://github.com/Ccccx159/Emby_Notifier"
CONTRIBUTORS = "xiaoQQya"

WELCOME_CONTENT = {
    "content": f"Welcome to {APP_NAME}!",
    "author": AUTHOR,
    "version": VERSION,
    "update_time": UPDATE_TIME,
    "intro": DESCRIPTION,
    "repo": REPOSITORY,
    "contributors": CONTRIBUTORS,
}
```

Create `src/emby_notifier/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import os


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AppConfig:
    tmdb_api_token: str
    telegram_bot_token: str
    telegram_chat_id: str
    tvdb_api_key: str | None
    tmdb_image_domain: str
    log_level: str
    log_export: bool
    log_path: str
    host: str
    port: int
    episode_buffer_timeout: int
    request_timeout: int


def _required(name: str, errors: list[str]) -> str:
    value = os.getenv(name)
    if not value:
        errors.append(name)
        return ""
    return value


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc


def load_config() -> AppConfig:
    errors: list[str] = []
    tmdb_api_token = _required("TMDB_API_TOKEN", errors)
    telegram_bot_token = _required("TG_BOT_TOKEN", errors)
    telegram_chat_id = _required("TG_CHAT_ID", errors)

    if errors:
        raise ConfigError("Missing required environment variables: " + ", ".join(errors))

    return AppConfig(
        tmdb_api_token=tmdb_api_token,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        tvdb_api_key=os.getenv("TVDB_API_KEY") or None,
        tmdb_image_domain=os.getenv("TMDB_IMAGE_DOMAIN", "https://image.tmdb.org").rstrip("/"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_export=os.getenv("LOG_EXPORT", "False") == "True",
        log_path=os.getenv("LOG_PATH", "/var/tmp/emby_notifier_tg"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=_int_env("PORT", 8000),
        episode_buffer_timeout=_int_env("EPISODE_BUFFER_TIMEOUT", 10),
        request_timeout=_int_env("REQUEST_TIMEOUT", 8),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_config.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add pyproject.toml src/emby_notifier/__init__.py src/emby_notifier/constants.py src/emby_notifier/config.py tests/test_config.py
git commit -m "test: 添加配置加载测试" -m "为新的包结构建立 pytest 基础，并覆盖必填环境变量校验与默认值加载，为后续架构迁移提供测试入口。"
```

## Task 2: Emby Event Domain Parser

**Files:**
- Create: `src/emby_notifier/utils/datetime.py`
- Create: `src/emby_notifier/domain/events.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write failing event parser tests**

Create `tests/test_events.py`:

```python
import json

from emby_notifier.domain.events import EventKind, parse_emby_event


def test_parse_movie_library_new_event():
    payload = {
        "Title": "New movie",
        "Event": "library.new",
        "Item": {
            "Type": "Movie",
            "Name": "Dune",
            "PremiereDate": "2021-09-15T00:00:00.0000000Z",
            "ProviderIds": {"Tmdb": "438631"},
        },
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
    }

    event = parse_emby_event(json.dumps(payload))

    assert event.kind == EventKind.MEDIA_ADDED
    assert event.item.media_type == "Movie"
    assert event.item.name == "Dune"
    assert event.item.premiere_year == 2021
    assert event.server.name == "Home"
    assert event.server.url == "https://emby.media"


def test_parse_episode_library_new_event():
    payload = {
        "Title": "New episode",
        "Event": "library.new",
        "Item": {
            "Type": "Episode",
            "SeriesName": "Foundation",
            "PremiereDate": "2023-07-14T00:00:00.0000000Z",
            "IndexNumber": 2,
            "ParentIndexNumber": 1,
            "ProviderIds": {"Tvdb": "123"},
            "SeriesId": "series-1",
            "SeasonId": "season-1",
        },
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
    }

    event = parse_emby_event(json.dumps(payload))

    assert event.kind == EventKind.MEDIA_ADDED
    assert event.item.media_type == "Episode"
    assert event.item.name == "Foundation"
    assert event.item.episode_number == 2
    assert event.item.season_number == 1
    assert event.buffer_key == "series-1_season-1"


def test_parse_notification_test_event():
    payload = {
        "Title": "Test",
        "Event": "system.notificationtest",
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
    }

    event = parse_emby_event(json.dumps(payload))

    assert event.kind == EventKind.TEST
    assert event.server.name == "Home"


def test_unsupported_event_is_skipped():
    payload = {"Title": "Other", "Event": "library.deleted", "Server": {"Name": "Home"}}

    event = parse_emby_event(json.dumps(payload))

    assert event.kind == EventKind.SKIP
    assert "Unsupported event type" in event.reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_events.py -v`

Expected: FAIL with `ModuleNotFoundError` or missing parser symbols.

- [ ] **Step 3: Implement event parser**

Create `src/emby_notifier/utils/datetime.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re


def iso8601_convert_cst(iso_time_str: str) -> datetime:
    utc_time = datetime.strptime(iso_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    cst_timezone = timezone(timedelta(hours=8))
    return utc_time.replace(tzinfo=timezone.utc).astimezone(cst_timezone)


def emby_version_at_least_4_8(version: str | None) -> bool:
    if not version:
        return False
    match = re.match(r"^(\d+)\.(\d+)", version)
    if not match:
        return False
    major, minor = map(int, match.groups())
    return major > 4 or (major == 4 and minor >= 8)


def parse_premiere_year(value: str | int | None, server_version: str | None) -> int:
    if value is None or value == "":
        return -1
    text = str(value)
    if text.isdigit():
        return int(text)
    if emby_version_at_least_4_8(server_version):
        return datetime.fromisoformat(text.replace("Z", "+00:00")).year
    return iso8601_convert_cst(text).year
```

Create `src/emby_notifier/domain/events.py` with dataclasses for `EventKind`, `ServerInfo`, `MediaItem`, `ParsedEvent`, and `parse_emby_event(raw: str) -> ParsedEvent`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_events.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/emby_notifier/utils/datetime.py src/emby_notifier/domain/events.py tests/test_events.py
git commit -m "feat: 添加 Emby 事件解析模型" -m "将 webhook JSON 转换为明确的领域事件，删除 Jellyfin 分支的设计依赖，并为电影、剧集、测试事件和跳过事件建立测试。"
```

## Task 3: Telegram Client And Notifier

**Files:**
- Create: `src/emby_notifier/utils/text.py`
- Create: `src/emby_notifier/domain/media.py`
- Create: `src/emby_notifier/clients/telegram.py`
- Create: `src/emby_notifier/notifiers/telegram.py`
- Test: `tests/test_telegram_notifier.py`

- [ ] **Step 1: Write failing Telegram formatting tests**

Create `tests/test_telegram_notifier.py`:

```python
from emby_notifier.constants import WELCOME_CONTENT
from emby_notifier.domain.media import AggregatedMediaDetail, MediaDetail
from emby_notifier.notifiers.telegram import TelegramNotifier


class FakeTelegramClient:
    def __init__(self):
        self.messages = []
        self.photos = []

    def send_message(self, text):
        self.messages.append(text)

    def send_photo(self, caption, photo):
        self.photos.append({"caption": caption, "photo": photo})


def movie_detail():
    return MediaDetail(
        server_type="Emby",
        server_name="Home_Server",
        server_url="https://emby.media",
        media_name="Dune",
        media_type="Movie",
        media_rating=8.1,
        media_rel="2021-09-15",
        media_intro="Desert power.",
        media_tmdburl="https://www.themoviedb.org/movie/438631?language=zh-CN",
        media_poster="https://image.tmdb.org/t/p/w500/poster.jpg",
        media_backdrop="https://image.tmdb.org/t/p/w500/backdrop.jpg",
    )


def episode_detail():
    return MediaDetail(
        server_type="Emby",
        server_name="Home",
        server_url="https://emby.media",
        media_name="Foundation",
        media_type="Episode",
        media_rating=7.5,
        media_rel="2023-07-14",
        media_intro="The empire shifts.",
        media_tmdburl="https://www.themoviedb.org/tv/93740?language=zh-CN",
        media_poster="https://image.tmdb.org/t/p/w500/poster.jpg",
        media_still="https://image.tmdb.org/t/p/w500/still.jpg",
        tv_season=1,
        tv_episode=2,
        tv_episode_name="Preparing to Live",
    )


def test_send_welcome_uses_message_api():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)

    notifier.send_welcome(WELCOME_CONTENT)

    assert len(client.messages) == 1
    assert "Welcome to Emby Notifier" in client.messages[0]
    assert "Version:" in client.messages[0]


def test_send_test_message_mentions_server_name():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)

    notifier.send_test("Home")

    assert len(client.messages) == 1
    assert "Emby Notifier worked" in client.messages[0]
    assert "Home" in client.messages[0]


def test_send_movie_uses_photo_with_movie_caption():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)

    notifier.send_media(movie_detail())

    assert client.photos[0]["photo"] == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert "[电影]" in client.photos[0]["caption"]
    assert "Dune" in client.photos[0]["caption"]


def test_send_episode_includes_season_episode_text():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)

    notifier.send_media(episode_detail())

    assert "已更新至 第1季 第2集" in client.photos[0]["caption"]
    assert "Preparing to Live" in client.photos[0]["caption"]


def test_send_aggregated_episode_uses_range_text():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)
    aggregated = AggregatedMediaDetail(
        detail=episode_detail(),
        tv_episode_min=2,
        tv_episode_max=4,
        tv_episode_total=3,
        tv_episode_list=(2, 3, 4),
    )

    notifier.send_aggregated_media(aggregated)

    assert "第2-4集 共3集" in client.photos[0]["caption"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_telegram_notifier.py -v`

Expected: FAIL because notifier modules do not exist.

- [ ] **Step 3: Implement media dataclasses and Telegram notifier**

Create dataclasses:

```python
@dataclass(frozen=True)
class MediaDetail:
    server_type: str
    server_name: str
    server_url: str
    media_name: str
    media_type: str
    media_rating: float
    media_rel: str
    media_intro: str
    media_tmdburl: str
    media_poster: str
    media_backdrop: str | None = None
    media_still: str | None = None
    tv_season: int | None = None
    tv_episode: int | None = None
    tv_episode_name: str | None = None


@dataclass(frozen=True)
class AggregatedMediaDetail:
    detail: MediaDetail
    tv_episode_min: int
    tv_episode_max: int
    tv_episode_total: int
    tv_episode_list: tuple[int, ...]
```

Implement `TelegramClient.send_message`, `TelegramClient.send_photo`, `TelegramNotifier.send_welcome`, `send_test`, `send_media`, and `send_aggregated_media`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_telegram_notifier.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/emby_notifier/utils/text.py src/emby_notifier/domain/media.py src/emby_notifier/clients/telegram.py src/emby_notifier/notifiers/telegram.py tests/test_telegram_notifier.py
git commit -m "feat: 添加 Telegram 通知器" -m "将 TG Bot API 调用与消息格式化拆分，保留欢迎、测试、影片、单集和聚合剧集通知行为。"
```

## Task 4: Metadata Clients And Media Enricher

**Files:**
- Create: `src/emby_notifier/clients/tmdb.py`
- Create: `src/emby_notifier/clients/tvdb.py`
- Create: `src/emby_notifier/services/media_enricher.py`
- Test: `tests/test_media_enricher.py`

- [ ] **Step 1: Write failing enricher tests**

Create `tests/test_media_enricher.py`:

```python
from emby_notifier.domain.events import MediaItem, ServerInfo
from emby_notifier.services.media_enricher import MediaEnricher


class FakeTMDB:
    def __init__(self):
        self.image_domain = "https://image.tmdb.org"

    def search_media(self, media_type, name, year):
        return [{"id": "93740", "original_name": name, "first_air_date": f"{year}-01-01"}]

    def get_external_ids(self, media_type, tmdb_id):
        return {"tvdb_id": 999}

    def get_movie_details(self, tmdb_id):
        return {
            "title": "Dune",
            "vote_average": 8.1,
            "release_date": "2021-09-15",
            "overview": "Desert power.",
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
        }

    def get_tv_episode_details(self, tmdb_id, season_number, episode_number):
        return {
            "vote_average": 7.5,
            "air_date": None,
            "overview": "The empire shifts.",
            "season_number": season_number,
            "episode_number": episode_number,
            "name": "Preparing to Live",
            "still_path": None,
        }

    def get_tv_season_details(self, tmdb_id, season_number):
        return {"air_date": "2023-07-14", "poster_path": "/season.jpg"}


class FakeTVDB:
    def get_series_id_by_episode_id(self, episode_id):
        return 999


def server():
    return ServerInfo(name="Home", version="4.8.0.80", url="https://emby.media", server_type="Emby")


def test_enrich_movie_uses_existing_tmdb_id():
    item = MediaItem(
        media_type="Movie",
        name="Dune",
        premiere_year=2021,
        provider_ids={"Tmdb": "438631"},
    )

    detail = MediaEnricher(FakeTMDB(), FakeTVDB()).enrich(item, server())

    assert detail.media_name == "Dune"
    assert detail.media_type == "Movie"
    assert detail.media_poster == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert detail.media_backdrop == "https://image.tmdb.org/t/p/w500/backdrop.jpg"


def test_enrich_episode_uses_tvdb_and_falls_back_to_season_data():
    item = MediaItem(
        media_type="Episode",
        name="Foundation",
        premiere_year=2023,
        provider_ids={"Tvdb": "123"},
        season_number=1,
        episode_number=2,
    )

    detail = MediaEnricher(FakeTMDB(), FakeTVDB()).enrich(item, server())

    assert detail.media_name == "Foundation"
    assert detail.media_type == "Episode"
    assert detail.media_rel == "2023-07-14"
    assert detail.media_still == "https://image.tmdb.org/t/p/w500/season.jpg"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_media_enricher.py -v`

Expected: FAIL because media enricher does not exist.

- [ ] **Step 3: Implement clients and enricher**

Implement clients as thin wrappers around `requests.Session` with `timeout=config.request_timeout`. Implement `MediaEnricher.enrich(item, server)` returning `MediaDetail`. Preserve existing TMDB URL format and image URL construction.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_media_enricher.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/emby_notifier/clients/tmdb.py src/emby_notifier/clients/tvdb.py src/emby_notifier/services/media_enricher.py tests/test_media_enricher.py
git commit -m "feat: 添加媒体详情补全服务" -m "隔离 TMDB 与 TVDB 访问，将电影和剧集详情组装为内部媒体模型，并用 fake client 测试核心分支。"
```

## Task 5: Processor, Episode Buffer, Server, And App Wiring

**Files:**
- Create: `src/emby_notifier/services/episode_buffer.py`
- Create: `src/emby_notifier/services/processor.py`
- Create: `src/emby_notifier/logging.py`
- Create: `src/emby_notifier/server.py`
- Create: `src/emby_notifier/app.py`
- Modify: `main.py`
- Test: `tests/test_episode_buffer.py`
- Test: `tests/test_processor.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_episode_buffer.py`:

```python
from emby_notifier.domain.media import MediaDetail
from emby_notifier.services.episode_buffer import EpisodeBuffer


class FakeNotifier:
    def __init__(self):
        self.media = []
        self.aggregated = []

    def send_media(self, detail):
        self.media.append(detail)

    def send_aggregated_media(self, detail):
        self.aggregated.append(detail)


def detail(episode):
    return MediaDetail(
        server_type="Emby",
        server_name="Home",
        server_url="https://emby.media",
        media_name="Foundation",
        media_type="Episode",
        media_rating=7.5,
        media_rel="2023-07-14",
        media_intro="The empire shifts.",
        media_tmdburl="https://www.themoviedb.org/tv/93740?language=zh-CN",
        media_poster="poster",
        tv_season=1,
        tv_episode=episode,
    )


def test_flush_single_episode_sends_single_media():
    notifier = FakeNotifier()
    buffer = EpisodeBuffer(notifier, timeout_seconds=30, auto_start_timer=False)

    buffer.add("foundation_1", detail(2), 2)
    buffer.flush("foundation_1")

    assert len(notifier.media) == 1
    assert notifier.media[0].tv_episode == 2
    assert notifier.aggregated == []


def test_flush_multiple_episodes_sends_aggregate():
    notifier = FakeNotifier()
    buffer = EpisodeBuffer(notifier, timeout_seconds=30, auto_start_timer=False)

    buffer.add("foundation_1", detail(2), 2)
    buffer.add("foundation_1", detail(4), 4)
    buffer.add("foundation_1", detail(3), 3)
    buffer.flush("foundation_1")

    assert notifier.media == []
    assert notifier.aggregated[0].tv_episode_min == 2
    assert notifier.aggregated[0].tv_episode_max == 4
    assert notifier.aggregated[0].tv_episode_total == 3
    assert notifier.aggregated[0].tv_episode_list == (2, 3, 4)
```

Create `tests/test_processor.py`:

```python
import json

from emby_notifier.domain.media import MediaDetail
from emby_notifier.services.processor import Processor


class FakeNotifier:
    def __init__(self):
        self.tests = []
        self.media = []

    def send_test(self, server_name):
        self.tests.append(server_name)

    def send_media(self, detail):
        self.media.append(detail)

    def send_aggregated_media(self, detail):
        raise AssertionError("not expected")


class FakeEnricher:
    def enrich(self, item, server):
        return MediaDetail(
            server_type=server.server_type,
            server_name=server.name,
            server_url=server.url,
            media_name=item.name,
            media_type=item.media_type,
            media_rating=8.0,
            media_rel="2021-09-15",
            media_intro="intro",
            media_tmdburl="tmdb",
            media_poster="poster",
        )


class FakeBuffer:
    def __init__(self):
        self.added = []

    def add(self, buffer_key, detail, episode_number):
        self.added.append((buffer_key, detail, episode_number))


def test_processor_sends_test_message():
    notifier = FakeNotifier()
    processor = Processor(FakeEnricher(), notifier, FakeBuffer())
    raw = json.dumps({"Event": "system.notificationtest", "Server": {"Name": "Home"}})

    result = processor.process_raw_message(raw)

    assert result == "test"
    assert notifier.tests == ["Home"]


def test_processor_sends_movie_immediately():
    notifier = FakeNotifier()
    processor = Processor(FakeEnricher(), notifier, FakeBuffer())
    raw = json.dumps({
        "Title": "New movie",
        "Event": "library.new",
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
        "Item": {
            "Type": "Movie",
            "Name": "Dune",
            "PremiereDate": "2021-09-15T00:00:00.0000000Z",
            "ProviderIds": {"Tmdb": "438631"},
        },
    })

    result = processor.process_raw_message(raw)

    assert result == "media"
    assert notifier.media[0].media_name == "Dune"


def test_processor_buffers_episode():
    buffer = FakeBuffer()
    processor = Processor(FakeEnricher(), FakeNotifier(), buffer)
    raw = json.dumps({
        "Title": "New episode",
        "Event": "library.new",
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
        "Item": {
            "Type": "Episode",
            "SeriesName": "Foundation",
            "PremiereDate": "2023-07-14T00:00:00.0000000Z",
            "IndexNumber": 2,
            "ParentIndexNumber": 1,
            "ProviderIds": {"Tvdb": "123"},
            "SeriesId": "series-1",
            "SeasonId": "season-1",
        },
    })

    result = processor.process_raw_message(raw)

    assert result == "buffered"
    assert buffer.added[0][0] == "series-1_season-1"
    assert buffer.added[0][2] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_episode_buffer.py tests/test_processor.py -v`

Expected: FAIL because service modules do not exist.

- [ ] **Step 3: Implement buffer and processor**

Implement `EpisodeBuffer.add(buffer_key, detail, episode_number)`, `EpisodeBuffer.flush(buffer_key)`, and `Processor.process_raw_message(raw)`. Processor should catch JSON parsing and per-message exceptions at the worker boundary, not inside domain parsing tests.

- [ ] **Step 4: Implement server and startup wiring**

`server.py` should expose `async def run_server(config, processor, logger)` and return `415` for non-JSON content type. `app.py` should load config, configure logging, validate TMDB and Telegram credentials, construct clients, send welcome, and start the server. `main.py` should contain only:

```python
from emby_notifier.app import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run service tests to verify they pass**

Run: `PYTHONPATH=src pytest tests/test_episode_buffer.py tests/test_processor.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/emby_notifier/services/episode_buffer.py src/emby_notifier/services/processor.py src/emby_notifier/logging.py src/emby_notifier/server.py src/emby_notifier/app.py main.py tests/test_episode_buffer.py tests/test_processor.py
git commit -m "feat: 串联 Emby TG 处理流程" -m "建立异步 webhook 服务、消息处理器、剧集聚合缓冲和应用启动编排，让新包结构具备完整运行路径。"
```

## Task 6: Remove Legacy Channels And Update Packaging

**Files:**
- Delete: `bark.py`
- Delete: `wxapp.py`
- Delete: `sender.py`
- Delete: `media.py`
- Delete: `tmdb_api.py`
- Delete: `tvdb_api.py`
- Delete: `tgbot.py`
- Delete: `my_httpd.py`
- Delete: `my_utils.py`
- Delete: `log.py`
- Delete: `dockerfile-aarch64`
- Modify: `dockerfile`
- Modify: `docker-compose.yml`
- Modify: `.github/workflows/docker-image.yml`

- [ ] **Step 1: Run full tests before deleting legacy files**

Run: `PYTHONPATH=src pytest -v`

Expected: PASS.

- [ ] **Step 2: Delete legacy files and update Dockerfile**

Replace `dockerfile` with an ARM Python base image that copies local files:

```dockerfile
FROM arm64v8/python:3.11-alpine3.19

LABEL maintainer="Xu@nCh3n"

ENV TZ=Asia/Shanghai LANG=zh_CN.UTF-8 PYTHONUNBUFFERED=1

WORKDIR /usr/src/myapp
EXPOSE 8000

COPY pyproject.toml ./
COPY src ./src
COPY main.py ./

RUN python3 -m pip install --no-cache-dir .

ENTRYPOINT ["python3"]
CMD ["/usr/src/myapp/main.py"]
```

Update GitHub Actions `platforms` to `linux/arm64`. Update compose env vars to include only `TMDB_API_TOKEN`, `TG_BOT_TOKEN`, `TG_CHAT_ID`, `TVDB_API_KEY`, `LOG_LEVEL`, `LOG_EXPORT`, and `LOG_PATH`.

- [ ] **Step 3: Run tests after deletion**

Run: `PYTHONPATH=src pytest -v`

Expected: PASS.

- [ ] **Step 4: Build ARM Docker image locally when Docker is available**

Run: `docker buildx build --platform linux/arm64 -f dockerfile -t emby-notifier:arm64-test --load .`

Expected: exit 0. If Docker is unavailable in the environment, record the exact error and do not claim Docker build passed.

- [ ] **Step 5: Commit**

Run:

```bash
git add -A bark.py wxapp.py sender.py media.py tmdb_api.py tvdb_api.py tgbot.py my_httpd.py my_utils.py log.py dockerfile dockerfile-aarch64 docker-compose.yml .github/workflows/docker-image.yml
git commit -m "build: 收敛为 ARM Telegram 镜像" -m "删除 Jellyfin、企业微信和 Bark 相关旧模块，将 Docker 构建改为复制本地包源码，并让 CI 只构建 linux/arm64 镜像。"
```

## Task 7: README Rewrite And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `version.txt`

- [ ] **Step 1: Rewrite README for supported scope**

Keep sections for introduction, requirements, environment variables, Docker run, docker-compose, Emby webhook setup, limitations, and references. Remove Jellyfin, WeChat Work, and Bark content and screenshots from the active instructions.

- [ ] **Step 2: Update version**

Set `version.txt` to:

```text
4.2.0
```

- [ ] **Step 3: Run full verification**

Run:

```bash
PYTHONPATH=src pytest -v
python -m compileall src main.py
```

Expected: both commands exit 0.

- [ ] **Step 4: Commit**

Run:

```bash
git add README.md version.txt
git commit -m "docs: 更新 Emby TG 使用说明" -m "将文档改写为 Emby-only 与 Telegram-only 的使用方式，并同步版本号到 4.2.0。"
```

## Final Check

- [ ] Run `git status --short` and confirm only unrelated `AGENTS.md` remains untracked if it was present before.
- [ ] Run `PYTHONPATH=src pytest -v`.
- [ ] Run `python -m compileall src main.py`.
- [ ] Run Docker ARM build if Docker is available.
- [ ] Summarize commits, verification output, and any Docker availability limitation.
