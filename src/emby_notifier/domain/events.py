from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json

from emby_notifier.utils.datetime import parse_premiere_year


class EventKind(str, Enum):
    MEDIA_ADDED = "media_added"
    TEST = "test"
    SKIP = "skip"


@dataclass(frozen=True)
class ServerInfo:
    name: str
    version: str | None = None
    url: str = "https://emby.media"
    server_type: str = "Emby"


@dataclass(frozen=True)
class MediaItem:
    media_type: str
    name: str
    premiere_year: int
    provider_ids: dict[str, str]
    season_number: int | None = None
    episode_number: int | None = None
    series_id: str | None = None
    season_id: str | None = None


@dataclass(frozen=True)
class ParsedEvent:
    kind: EventKind
    title: str
    server: ServerInfo
    item: MediaItem | None = None
    reason: str | None = None

    @property
    def buffer_key(self) -> str | None:
        if self.item is None or self.item.media_type != "Episode":
            return None
        if self.item.series_id and self.item.season_id:
            return f"{self.item.series_id}_{self.item.season_id}"
        season_number = self.item.season_number if self.item.season_number is not None else "unknown"
        return f"{self.item.name}_{season_number}"


def parse_emby_event(raw: str) -> ParsedEvent:
    payload = json.loads(raw)
    server = _parse_server(payload.get("Server", {}))
    title = payload.get("Title", "")
    event_type = payload.get("Event", "")

    if event_type == "system.notificationtest":
        return ParsedEvent(kind=EventKind.TEST, title=title, server=server)
    if event_type != "library.new":
        return ParsedEvent(
            kind=EventKind.SKIP,
            title=title,
            server=server,
            reason=f"Unsupported event type: {event_type}",
        )

    item_payload = payload.get("Item", {})
    media_type = item_payload.get("Type")
    if media_type not in {"Movie", "Episode"}:
        return ParsedEvent(
            kind=EventKind.SKIP,
            title=title,
            server=server,
            reason=f"Unsupported media type: {media_type}",
        )

    item = _parse_item(item_payload, server)
    return ParsedEvent(kind=EventKind.MEDIA_ADDED, title=title, server=server, item=item)


def _parse_server(payload: dict) -> ServerInfo:
    return ServerInfo(
        name=payload.get("Name", "Unknown"),
        version=payload.get("Version"),
        url=payload.get("Url", "https://emby.media"),
        server_type="Emby",
    )


def _parse_item(payload: dict, server: ServerInfo) -> MediaItem:
    media_type = payload["Type"]
    if media_type == "Movie":
        name = payload.get("Name", "")
    else:
        name = payload.get("SeriesName", payload.get("Name", ""))

    return MediaItem(
        media_type=media_type,
        name=name,
        premiere_year=parse_premiere_year(payload.get("PremiereDate"), server.version),
        provider_ids=dict(payload.get("ProviderIds", {})),
        season_number=payload.get("ParentIndexNumber"),
        episode_number=payload.get("IndexNumber"),
        series_id=payload.get("SeriesId"),
        season_id=payload.get("SeasonId"),
    )
