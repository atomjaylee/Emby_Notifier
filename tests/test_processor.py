import json

from emby_notifier.domain.media import MediaDetail
from emby_notifier.services.processor import Processor


class FakeNotifier:
    def __init__(self):
        self.tests = []
        self.media = []

    def send_test(self, server_name):
        self.tests.append(server_name)

    def send_media(self, detail):
        self.media.append(detail)

    def send_aggregated_media(self, detail):
        raise AssertionError("not expected")


class FakeEnricher:
    def enrich(self, item, server):
        return MediaDetail(
            server_type=server.server_type,
            server_name=server.name,
            server_url=server.url,
            media_name=item.name,
            media_type=item.media_type,
            media_rating=8.0,
            media_rel="2021-09-15",
            media_intro="intro",
            media_tmdburl="tmdb",
            media_poster="poster",
            tv_episode=item.episode_number,
            tv_season=item.season_number,
        )


class FakeBuffer:
    def __init__(self):
        self.added = []

    def add(self, buffer_key, detail, episode_number):
        self.added.append((buffer_key, detail, episode_number))


def test_processor_sends_test_message():
    notifier = FakeNotifier()
    processor = Processor(FakeEnricher(), notifier, FakeBuffer())
    raw = json.dumps({"Event": "system.notificationtest", "Server": {"Name": "Home"}})

    result = processor.process_raw_message(raw)

    assert result == "test"
    assert notifier.tests == ["Home"]


def test_processor_sends_movie_immediately():
    notifier = FakeNotifier()
    processor = Processor(FakeEnricher(), notifier, FakeBuffer())
    raw = json.dumps({
        "Title": "New movie",
        "Event": "library.new",
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
        "Item": {
            "Type": "Movie",
            "Name": "Dune",
            "PremiereDate": "2021-09-15T00:00:00.0000000Z",
            "ProviderIds": {"Tmdb": "438631"},
        },
    })

    result = processor.process_raw_message(raw)

    assert result == "media"
    assert notifier.media[0].media_name == "Dune"


def test_processor_buffers_episode():
    buffer = FakeBuffer()
    processor = Processor(FakeEnricher(), FakeNotifier(), buffer)
    raw = json.dumps({
        "Title": "New episode",
        "Event": "library.new",
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
        "Item": {
            "Type": "Episode",
            "SeriesName": "Foundation",
            "PremiereDate": "2023-07-14T00:00:00.0000000Z",
            "IndexNumber": 2,
            "ParentIndexNumber": 1,
            "ProviderIds": {"Tvdb": "123"},
            "SeriesId": "series-1",
            "SeasonId": "season-1",
        },
    })

    result = processor.process_raw_message(raw)

    assert result == "buffered"
    assert buffer.added[0][0] == "series-1_season-1"
    assert buffer.added[0][2] == 2
