from __future__ import annotations

import time

from emby_notifier.domain.media import AggregatedMediaDetail, MediaDetail
from emby_notifier.utils.text import escape_telegram_markdown


class TelegramNotifier:
    def __init__(self, client):
        self.client = client

    def send_welcome(self, welcome: dict) -> None:
        message = (
            f"{welcome['content']}\n"
            f"Author: {welcome['author']}\n"
            f"Version: {welcome['version']}\n"
            f"Update Time: {welcome['update_time']}\n"
            f"Description: {welcome['intro']}\n"
            f"Repository: {welcome['repo']}\n"
        )
        self.client.send_message(escape_telegram_markdown(message))

    def send_test(self, server_name: str) -> None:
        message = (
            "*Congratulations!*\n\n"
            "Emby Notifier worked!\n\n"
            f"This is a test message from *{escape_telegram_markdown(server_name)}*.\n\n"
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
        )
        self.client.send_message(message)

    def send_media(self, media: MediaDetail) -> None:
        caption = self._build_caption(media)
        self.client.send_photo(caption, _preview_image(media))

    def send_aggregated_media(self, media: AggregatedMediaDetail) -> None:
        caption = self._build_caption(
            media.detail,
            f"📌 已更新至 第{media.detail.tv_season}季 第{media.tv_episode_min}-{media.tv_episode_max}集 共{media.tv_episode_total}集\n",
            title=media.detail.media_name,
            approximate_size=True,
        )
        self.client.send_photo(caption, _preview_image(media.detail))

    def _build_caption(
        self,
        media: MediaDetail,
        episode_text: str | None = None,
        title: str | None = None,
        approximate_size: bool = False,
    ) -> str:
        if episode_text is None:
            episode_text = (
                f"📌 已更新至 第{media.tv_season}季 第{media.tv_episode}集\n"
                if media.media_type == "Episode"
                else ""
            )

        if title is None:
            title = (
                media.media_name
                if media.media_type == "Movie"
                else f"{media.media_name} {media.tv_episode_name or ''}".strip()
            )

        media_type = "🎬 电影入库" if media.media_type == "Movie" else "📺 剧集入库"
        year = media.media_rel[0:4] if media.media_rel else "Unknown"

        return (
            f"{media_type}\n"
            f"🎞️ 片名： *{escape_telegram_markdown(title)}* ({year})\n"
            f"{episode_text}"
            f"{self._technical_text(media, approximate_size=approximate_size)}"
            f"📅 上映日期： {media.media_rel}\n"
            f"🔗 相关链接： [TMDB]({media.media_tmdburl})\n"
        )

    def _technical_text(self, media: MediaDetail, approximate_size: bool) -> str:
        info = media.technical_info
        if info is None:
            return ""

        lines = []
        quality = " · ".join(part for part in (info.quality, info.dynamic_range) if part)
        if quality:
            lines.append(f"🧩 画质：{quality}")
        if info.subtitle:
            lines.append(f"💬 字幕：{info.subtitle}")
        if info.size_gb is not None:
            if approximate_size:
                lines.append(f"💾 大小：约 {_format_size(info.size_gb)}/集")
            else:
                lines.append(f"💾 大小：{_format_size(info.size_gb)}")

        return "\n".join(lines) + ("\n" if lines else "")


def _format_size(size_gb: float) -> str:
    text = f"{size_gb:.2f}".rstrip("0").rstrip(".")
    return f"{text} GB"


def _preview_image(media: MediaDetail) -> str:
    return media.media_still or media.media_backdrop or media.media_poster
