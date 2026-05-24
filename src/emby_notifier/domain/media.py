from __future__ import annotations

from dataclasses import dataclass


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
