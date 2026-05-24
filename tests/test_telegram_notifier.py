from dataclasses import replace

from emby_notifier.constants import WELCOME_CONTENT
from emby_notifier.domain.media import AggregatedMediaDetail, MediaDetail, MediaTechnicalInfo
from emby_notifier.notifiers.telegram import TelegramNotifier


class FakeTelegramClient:
    def __init__(self):
        self.messages = []
        self.photos = []

    def send_message(self, text):
        self.messages.append(text)

    def send_photo(self, caption, photo, show_caption_above_media=False):
        self.photos.append({
            "caption": caption,
            "photo": photo,
            "show_caption_above_media": show_caption_above_media,
        })


def movie_detail():
    return MediaDetail(
        server_type="Emby",
        server_name="Home_Server",
        server_url="https://emby.media",
        media_name="Dune",
        media_type="Movie",
        media_rating=8.1,
        media_rel="2021-09-15",
        media_intro="Desert power.",
        media_tmdburl="https://www.themoviedb.org/movie/438631?language=zh-CN",
        media_poster="https://image.tmdb.org/t/p/w500/poster.jpg",
        media_backdrop="https://image.tmdb.org/t/p/w500/backdrop.jpg",
        technical_info=MediaTechnicalInfo(
            quality="4K",
            dynamic_range="Dolby Vision",
            subtitle="简中特效",
            size_gb=18.6,
        ),
    )


def episode_detail(total_episodes=40, total_seasons=1, season=1):
    return MediaDetail(
        server_type="Emby",
        server_name="Home",
        server_url="https://emby.media",
        media_name="Foundation",
        media_type="Episode",
        media_rating=7.5,
        media_rel="2023-07-14",
        media_intro="The empire shifts.",
        media_tmdburl="https://www.themoviedb.org/tv/93740?language=zh-CN",
        media_poster="https://image.tmdb.org/t/p/w500/poster.jpg",
        media_still="https://image.tmdb.org/t/p/w500/still.jpg",
        tv_season=season,
        tv_episode=2,
        tv_season_episode_count=total_episodes,
        tv_total_seasons=total_seasons,
        tv_episode_name="Preparing to Live",
        technical_info=MediaTechnicalInfo(
            quality="4K",
            dynamic_range="HDR10",
            subtitle="简中特效",
            size_gb=3.42,
        ),
    )


def test_send_welcome_uses_message_api():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)

    notifier.send_welcome(WELCOME_CONTENT)

    assert len(client.messages) == 1
    assert "Welcome to Emby Notifier" in client.messages[0]
    assert "Version:" in client.messages[0]


def test_send_test_message_mentions_server_name():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)

    notifier.send_test("Home")

    assert len(client.messages) == 1
    assert "Emby Notifier worked" in client.messages[0]
    assert "Home" in client.messages[0]


def test_send_movie_uses_photo_with_movie_caption():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)

    notifier.send_media(movie_detail())

    assert client.photos[0]["photo"] == "https://image.tmdb.org/t/p/w342/poster.jpg"
    assert client.photos[0]["show_caption_above_media"] is False
    assert "#影视更新" not in client.photos[0]["caption"]
    assert "#Home_Server" not in client.photos[0]["caption"]
    assert "🎬 电影入库" in client.photos[0]["caption"]
    assert "Dune" in client.photos[0]["caption"]
    assert "内容简介" not in client.photos[0]["caption"]
    assert "Desert power." not in client.photos[0]["caption"]
    assert "🎞️ 片名： *Dune* (2021)" in client.photos[0]["caption"]
    assert "🧩 画质：4K · Dolby Vision" in client.photos[0]["caption"]
    assert "💬 字幕：简中特效" in client.photos[0]["caption"]
    assert "小组" not in client.photos[0]["caption"]
    assert "💾 大小：18.6 GB" in client.photos[0]["caption"]
    assert "评分" not in client.photos[0]["caption"]
    assert "⭐" not in client.photos[0]["caption"]


def test_send_movie_falls_back_to_message_without_image():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)
    detail = replace(movie_detail(), media_poster=None, media_backdrop=None, media_still=None)

    notifier.send_media(detail)

    assert client.photos == []
    assert len(client.messages) == 1
    assert "🎬 电影入库" in client.messages[0]
    assert "🎞️ 片名： *Dune* (2021)" in client.messages[0]


def test_send_episode_includes_season_episode_text():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)

    notifier.send_media(episode_detail())

    assert client.photos[0]["photo"] == "https://image.tmdb.org/t/p/w342/poster.jpg"
    assert "📺 剧集入库" in client.photos[0]["caption"]
    assert "📌 更新进度：2/40" in client.photos[0]["caption"]
    assert "Preparing to Live" in client.photos[0]["caption"]
    assert "🧩 画质：4K · HDR10" in client.photos[0]["caption"]
    assert "评分" not in client.photos[0]["caption"]


def test_send_aggregated_episode_uses_progress_text():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)
    aggregated = AggregatedMediaDetail(
        detail=episode_detail(),
        tv_episode_min=2,
        tv_episode_max=4,
        tv_episode_total=3,
        tv_episode_list=(2, 3, 4),
    )

    notifier.send_aggregated_media(aggregated)

    assert "📌 更新进度：4/40" in client.photos[0]["caption"]
    assert "第2-4集 共3集" not in client.photos[0]["caption"]
    assert "💾 大小：约 3.42 GB/集" in client.photos[0]["caption"]


def test_send_aggregated_episode_shows_completed_when_full_season_arrives():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)
    aggregated = AggregatedMediaDetail(
        detail=episode_detail(),
        tv_episode_min=1,
        tv_episode_max=40,
        tv_episode_total=40,
        tv_episode_list=tuple(range(1, 41)),
    )

    notifier.send_aggregated_media(aggregated)

    assert "📌 已完结 · 全40集" in client.photos[0]["caption"]
    assert "1/40" not in client.photos[0]["caption"]


def test_send_aggregated_episode_includes_season_when_multi_season_show_completed():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)
    aggregated = AggregatedMediaDetail(
        detail=episode_detail(total_seasons=3, season=2),
        tv_episode_min=1,
        tv_episode_max=40,
        tv_episode_total=40,
        tv_episode_list=tuple(range(1, 41)),
    )

    notifier.send_aggregated_media(aggregated)

    assert "📌 第2季已完结 · 全40集" in client.photos[0]["caption"]


def test_send_aggregated_episode_falls_back_to_range_without_tmdb_total():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)
    aggregated = AggregatedMediaDetail(
        detail=episode_detail(total_episodes=None),
        tv_episode_min=2,
        tv_episode_max=4,
        tv_episode_total=3,
        tv_episode_list=(2, 3, 4),
    )

    notifier.send_aggregated_media(aggregated)

    assert "📌 已更新至 第1季 第2-4集 共3集" in client.photos[0]["caption"]


def test_send_aggregated_episode_falls_back_to_message_without_image():
    client = FakeTelegramClient()
    notifier = TelegramNotifier(client)
    aggregated = AggregatedMediaDetail(
        detail=replace(episode_detail(), media_poster=None, media_backdrop=None, media_still=None),
        tv_episode_min=2,
        tv_episode_max=4,
        tv_episode_total=3,
        tv_episode_list=(2, 3, 4),
    )

    notifier.send_aggregated_media(aggregated)

    assert client.photos == []
    assert len(client.messages) == 1
    assert "📺 剧集入库" in client.messages[0]
    assert "📌 更新进度：4/40" in client.messages[0]
