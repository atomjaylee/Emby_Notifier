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
    tmdb_image_domain: str
    log_level: str
    log_export: bool
    log_path: str
    host: str
    port: int
    episode_buffer_timeout: int
    request_timeout: int
    emby_server_url: str | None
    emby_api_key: str | None
    emby_api_timeout: int


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
        tmdb_image_domain=os.getenv("TMDB_IMAGE_DOMAIN", "https://image.tmdb.org").rstrip("/"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_export=os.getenv("LOG_EXPORT", "False") == "True",
        log_path=os.getenv("LOG_PATH", "/var/tmp/emby_notifier_tg"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=_int_env("PORT", 8000),
        episode_buffer_timeout=_int_env("EPISODE_BUFFER_TIMEOUT", 180),
        request_timeout=_int_env("REQUEST_TIMEOUT", 8),
        emby_server_url=_optional_url("EMBY_SERVER_URL"),
        emby_api_key=os.getenv("EMBY_API_KEY") or None,
        emby_api_timeout=_int_env("EMBY_API_TIMEOUT", 5),
    )


def _optional_url(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    return value.rstrip("/")
