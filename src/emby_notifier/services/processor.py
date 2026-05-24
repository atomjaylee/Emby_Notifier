from __future__ import annotations

from emby_notifier.domain.events import EventKind, parse_emby_event


class Processor:
    def __init__(self, enricher, notifier, episode_buffer, logger=None, technical_enricher=None):
        self.enricher = enricher
        self.notifier = notifier
        self.episode_buffer = episode_buffer
        self.logger = logger
        self.technical_enricher = technical_enricher

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

        detail = self.enricher.enrich(event.item, event.server)
        if event.item.media_type == "Episode":
            episode_number = event.item.episode_number or detail.tv_episode or 0
            self.episode_buffer.add(
                event.buffer_key or event.item.name,
                detail,
                episode_number,
                event.item.item_id,
            )
            return "buffered"

        if self.technical_enricher is not None and event.item.item_id is not None:
            detail = self.technical_enricher.enrich(detail, event.item.item_id)
        self.notifier.send_media(detail)
        return "media"
