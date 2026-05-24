from emby_notifier.domain.media import MediaDetail
from emby_notifier.services.episode_buffer import EpisodeBuffer


class FakeNotifier:
    def __init__(self):
        self.media = []
        self.aggregated = []

    def send_media(self, detail):
        self.media.append(detail)

    def send_aggregated_media(self, detail):
        self.aggregated.append(detail)


class FakeTimer:
    instances = []

    def __init__(self, timeout, callback, args=()):
        self.timeout = timeout
        self.callback = callback
        self.args = args
        self.started = False
        self.cancelled = False
        FakeTimer.instances.append(self)

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def is_alive(self):
        return self.started and not self.cancelled


def fake_timer_factory(timeout, callback, args=()):
    return FakeTimer(timeout, callback, args)


def detail(episode):
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
        media_poster="poster",
        tv_season=1,
        tv_episode=episode,
    )


def test_flush_single_episode_sends_single_media():
    notifier = FakeNotifier()
    buffer = EpisodeBuffer(notifier, timeout_seconds=30, auto_start_timer=False)

    buffer.add("foundation_1", detail(2), 2)
    buffer.flush("foundation_1")

    assert len(notifier.media) == 1
    assert notifier.media[0].tv_episode == 2
    assert notifier.aggregated == []


def test_flush_multiple_episodes_sends_aggregate():
    notifier = FakeNotifier()
    buffer = EpisodeBuffer(notifier, timeout_seconds=30, auto_start_timer=False)

    buffer.add("foundation_1", detail(2), 2)
    buffer.add("foundation_1", detail(4), 4)
    buffer.add("foundation_1", detail(3), 3)
    buffer.flush("foundation_1")

    assert notifier.media == []
    assert notifier.aggregated[0].tv_episode_min == 2
    assert notifier.aggregated[0].tv_episode_max == 4
    assert notifier.aggregated[0].tv_episode_total == 3
    assert notifier.aggregated[0].tv_episode_list == (2, 3, 4)


def test_add_resets_timer_for_same_episode_group():
    FakeTimer.instances = []
    notifier = FakeNotifier()
    buffer = EpisodeBuffer(
        notifier,
        timeout_seconds=180,
        timer_factory=fake_timer_factory,
    )

    buffer.add("foundation_1", detail(2), 2)
    buffer.add("foundation_1", detail(3), 3)

    assert len(FakeTimer.instances) == 2
    assert FakeTimer.instances[0].cancelled is True
    assert FakeTimer.instances[1].started is True
    assert FakeTimer.instances[1].timeout == 180
