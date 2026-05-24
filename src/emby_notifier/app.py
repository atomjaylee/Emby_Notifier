from __future__ import annotations

import asyncio

from emby_notifier.clients.telegram import TelegramClient
from emby_notifier.clients.emby import EmbyClient
from emby_notifier.clients.tmdb import TMDBClient
from emby_notifier.config import load_config
from emby_notifier.constants import WELCOME_CONTENT
from emby_notifier.logging import configure_logger
from emby_notifier.notifiers.telegram import TelegramNotifier
from emby_notifier.server import run_server
from emby_notifier.services.episode_buffer import EpisodeBuffer
from emby_notifier.services.emby_metadata import EmbyTechnicalEnricher
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

    telegram_client = TelegramClient(
        config.telegram_bot_token,
        config.telegram_chat_id,
        timeout=config.request_timeout,
    )
    telegram_client.validate_bot()
    telegram_client.validate_chat()

    notifier = TelegramNotifier(telegram_client)
    notifier.send_welcome(WELCOME_CONTENT)

    technical_enricher = None
    if config.emby_server_url and config.emby_api_key:
        technical_enricher = EmbyTechnicalEnricher(
            EmbyClient(
                config.emby_server_url,
                config.emby_api_key,
                timeout=config.emby_api_timeout,
            ),
            logger=logger,
        )

    enricher = MediaEnricher(tmdb_client)
    episode_buffer = EpisodeBuffer(
        notifier,
        config.episode_buffer_timeout,
        technical_enricher=technical_enricher,
    )
    processor = Processor(
        enricher,
        notifier,
        episode_buffer,
        logger=logger,
        technical_enricher=technical_enricher,
    )
    await run_server(config, processor, logger)


def main() -> None:
    asyncio.run(async_main())
