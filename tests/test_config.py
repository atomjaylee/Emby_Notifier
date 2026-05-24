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
    monkeypatch.delenv("TMDB_IMAGE_DOMAIN", raising=False)
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("EPISODE_BUFFER_TIMEOUT", raising=False)
    monkeypatch.delenv("EMBY_SERVER_URL", raising=False)
    monkeypatch.delenv("EMBY_API_KEY", raising=False)
    monkeypatch.delenv("EMBY_API_TIMEOUT", raising=False)

    config = load_config()

    assert config.tmdb_api_token == "tmdb-token"
    assert config.telegram_bot_token == "tg-token"
    assert config.telegram_chat_id == "-100123"
    assert config.tmdb_image_domain == "https://image.tmdb.org"
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.episode_buffer_timeout == 180
    assert config.emby_server_url is None
    assert config.emby_api_key is None
    assert config.emby_api_timeout == 5


def test_load_config_accepts_optional_emby_api(monkeypatch):
    monkeypatch.setenv("TMDB_API_TOKEN", "tmdb-token")
    monkeypatch.setenv("TG_BOT_TOKEN", "tg-token")
    monkeypatch.setenv("TG_CHAT_ID", "-100123")
    monkeypatch.setenv("EMBY_SERVER_URL", "https://emby.example.com/")
    monkeypatch.setenv("EMBY_API_KEY", "emby-key")

    config = load_config()

    assert config.emby_server_url == "https://emby.example.com"
    assert config.emby_api_key == "emby-key"
