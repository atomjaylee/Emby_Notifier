from __future__ import annotations

import threading
from urllib.parse import urlparse

from emby_notifier.domain.events import EventKind, parse_emby_event


class Processor:
    def __init__(
        self,
        enricher,
        notifier,
        episode_buffer,
        logger=None,
        technical_enricher=None,
        movie_notify_delay: int = 60,
        timer_factory=threading.Timer,
    ):
        self.enricher = enricher
        self.notifier = notifier
        self.episode_buffer = episode_buffer
        self.logger = logger
        self.technical_enricher = technical_enricher
        self.movie_notify_delay = movie_notify_delay
        self.timer_factory = timer_factory

    def process_raw_message(self, raw: str) -> str:
        event = parse_emby_event(raw)

        if event.kind == EventKind.SKIP:
            if self.logger:
                self.logger.warning(event.reason)
            return "skip"

        if event.kind == EventKind.TEST:
            self.notifier.send_test(event.server.name)
            return "test"

        if event.item is None:
            if self.logger:
                self.logger.warning("Media event missing item payload")
            return "skip"

        if self.logger:
            self.logger.debug(
                f"Processing {event.item.media_type}: name={event.item.name}, "
                f"item_id={event.item.item_id}, providers={event.item.provider_ids}"
            )

        detail = self.enricher.enrich(event.item, event.server)

        if event.item.media_type == "Episode":
            episode_number = event.item.episode_number or detail.tv_episode or 0
            self.episode_buffer.add(
                event.buffer_key or event.item.name,
                detail,
                episode_number,
                event.item.item_id,
                _tmdb_id_from_detail(detail),
            )
            return "buffered"

        item_id = event.item.item_id
        tmdb_id = _tmdb_id_from_detail(detail)

        if self.movie_notify_delay > 0 and self.technical_enricher is not None and item_id is not None:
            if self.logger:
                self.logger.info(
                    f"Movie '{detail.media_name}' will be sent after {self.movie_notify_delay}s delay"
                )
            timer = self.timer_factory(
                self.movie_notify_delay,
                self._delayed_movie_send,
                args=(detail, item_id, tmdb_id),
            )
            timer.daemon = True
            timer.start()
            return "delayed"

        if self.technical_enricher is not None and item_id is not None:
            detail = self.technical_enricher.enrich(detail, item_id, tmdb_id=tmdb_id)
        self.notifier.send_media(detail)
        return "media"

    def _delayed_movie_send(self, detail, item_id: str, tmdb_id: str | None) -> None:
        try:
            if self.logger:
                self.logger.debug(f"Delayed movie send triggered for '{detail.media_name}'")
            detail = self.technical_enricher.enrich(detail, item_id, tmdb_id=tmdb_id)
            if self.logger:
                self.logger.debug(f"Technical info result: {detail.technical_info}")
            self.notifier.send_media(detail)
            if self.logger:
                self.logger.info(f"Movie '{detail.media_name}' notification sent")
        except Exception:
            if self.logger:
                import traceback
                self.logger.error(f"Delayed movie send failed: {traceback.format_exc()}")


def _tmdb_id_from_detail(detail) -> str | None:
    parsed = urlparse(detail.media_tmdburl)
    parts = [part for part in parsed.path.split("/") if part]
    return parts[-1] if parts else None
