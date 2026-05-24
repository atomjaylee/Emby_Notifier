from __future__ import annotations

import asyncio

from emby_notifier.clients.telegram import TelegramClient
from emby_notifier.clients.tmdb import TMDBClient
from emby_notifier.clients.tvdb import TVDBClient
from emby_notifier.config import load_config
from emby_notifier.constants import WELCOME_CONTENT
from emby_notifier.logging import configure_logger
from emby_notifier.notifiers.telegram import TelegramNotifier
from emby_notifier.server import run_server
from emby_notifier.services.episode_buffer import EpisodeBuffer
from emby_notifier.services.media_enricher import MediaEnricher
from emby_notifier.services.processor import Processor


async def async_main() -> None:
    config = load_config()
    logger = configure_logger(config.log_level, config.log_export, config.log_path)

    tmdb_client = TMDBClient(
        config.tmdb_api_token,
        config.tmdb_image_domain,
        timeout=config.request_timeout,
    )
    tmdb_client.validate()

    tvdb_client = (
        TVDBClient(config.tvdb_api_key, timeout=config.request_timeout)
        if config.tvdb_api_key
        else None
    )
    telegram_client = TelegramClient(
        config.telegram_bot_token,
        config.telegram_chat_id,
        timeout=config.request_timeout,
    )
    telegram_client.validate_bot()
    telegram_client.validate_chat()

    notifier = TelegramNotifier(telegram_client)
    notifier.send_welcome(WELCOME_CONTENT)

    enricher = MediaEnricher(tmdb_client, tvdb_client)
    episode_buffer = EpisodeBuffer(notifier, config.episode_buffer_timeout)
    processor = Processor(enricher, notifier, episode_buffer, logger=logger)
    await run_server(config, processor, logger)


def main() -> None:
    asyncio.run(async_main())
