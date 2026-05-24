from __future__ import annotations

from dataclasses import replace

from emby_notifier.domain.media import MediaDetail, MediaTechnicalInfo


class EmbyTechnicalEnricher:
    def __init__(self, emby_client, logger=None):
        self.emby_client = emby_client
        self.logger = logger

    def enrich(self, detail: MediaDetail, item_id: str, tmdb_id: str | None = None) -> MediaDetail:
        try:
            info = self.get_info(item_id, tmdb_id=tmdb_id)
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Unable to load Emby technical info for {item_id}: {exc}")
            return detail
        return replace(detail, technical_info=info)

    def get_info(self, item_id: str, tmdb_id: str | None = None) -> MediaTechnicalInfo:
        item = self._get_item(item_id, tmdb_id)
        media_source = _first_media_source(item)
        video_stream = _first_stream(media_source, "Video")
        subtitle_streams = _streams(media_source, "Subtitle")

        return MediaTechnicalInfo(
            quality=_quality(video_stream),
            dynamic_range=_dynamic_range(video_stream),
            subtitle=_subtitle_label(subtitle_streams),
            size_gb=_size_gb(media_source.get("Size") or item.get("Size")),
        )

    def _get_item(self, item_id: str, tmdb_id: str | None) -> dict:
        try:
            return self.emby_client.get_item(item_id)
        except Exception:
            if not tmdb_id or not hasattr(self.emby_client, "find_item_by_tmdb_id"):
                raise
            return self.emby_client.find_item_by_tmdb_id(tmdb_id, preferred_item_id=item_id)


def _first_media_source(item: dict) -> dict:
    sources = item.get("MediaSources") or []
    if sources:
        return sources[0]
    return item


def _streams(media_source: dict, stream_type: str) -> list[dict]:
    return [
        stream
        for stream in media_source.get("MediaStreams", [])
        if stream.get("Type") == stream_type
    ]


def _first_stream(media_source: dict, stream_type: str) -> dict:
    streams = _streams(media_source, stream_type)
    return streams[0] if streams else {}


def _quality(video_stream: dict) -> str | None:
    height = int(video_stream.get("Height") or 0)
    width = int(video_stream.get("Width") or 0)
    if height >= 2160 or width >= 3840:
        return "4K"
    if height >= 1080:
        return "1080p"
    if height >= 720:
        return "720p"
    return None


def _dynamic_range(video_stream: dict) -> str | None:
    value = " ".join(
        str(video_stream.get(key, ""))
        for key in ("VideoRange", "VideoRangeType", "Profile", "DisplayTitle")
    ).lower()
    if any(token in value for token in ("dovi", "dolby vision", "dvhe", "dv")):
        return "Dolby Vision"
    if "hdr10+" in value or "hdr10plus" in value:
        return "HDR10+"
    if "hdr10" in value:
        return "HDR10"
    if "hdr" in value:
        return "HDR"
    if "sdr" in value:
        return "SDR"
    return None


def _subtitle_label(subtitle_streams: list[dict]) -> str | None:
    chinese = [stream for stream in subtitle_streams if _is_chinese_subtitle(stream)]
    if not chinese:
        return None
    special = [stream for stream in chinese if _is_special_subtitle(stream)]
    selected = special[0] if special else chinese[0]
    language = _chinese_language_label(selected)
    return f"{language}特效" if _is_special_subtitle(selected) else language


def _is_chinese_subtitle(stream: dict) -> bool:
    text = _stream_text(stream)
    return any(token in text for token in ("chi", "zho", "chs", "cht", "中文", "简中", "繁中"))


def _is_special_subtitle(stream: dict) -> bool:
    text = _stream_text(stream)
    codec = str(stream.get("Codec", "")).lower()
    return codec in {"ass", "ssa"} or any(token in text for token in ("特效", "ass", "ssa"))


def _chinese_language_label(stream: dict) -> str:
    text = _stream_text(stream)
    if any(token in text for token in ("cht", "繁中", "繁体")):
        return "繁中"
    return "简中"


def _stream_text(stream: dict) -> str:
    return " ".join(str(value) for value in stream.values()).lower()


def _size_gb(size: int | str | None) -> float | None:
    if not size:
        return None
    try:
        return round(int(size) / 1024 / 1024 / 1024, 2)
    except (TypeError, ValueError):
        return None
