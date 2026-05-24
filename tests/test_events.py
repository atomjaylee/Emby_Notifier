import json

from emby_notifier.domain.events import EventKind, parse_emby_event


def test_parse_movie_library_new_event():
    payload = {
        "Title": "New movie",
        "Event": "library.new",
        "Item": {
            "Type": "Movie",
            "Name": "Dune",
            "PremiereDate": "2021-09-15T00:00:00.0000000Z",
            "ProviderIds": {"Tmdb": "438631"},
        },
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
    }

    event = parse_emby_event(json.dumps(payload))

    assert event.kind == EventKind.MEDIA_ADDED
    assert event.item.media_type == "Movie"
    assert event.item.name == "Dune"
    assert event.item.premiere_year == 2021
    assert event.server.name == "Home"
    assert event.server.url == "https://emby.media"


def test_parse_episode_library_new_event():
    payload = {
        "Title": "New episode",
        "Event": "library.new",
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
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
    }

    event = parse_emby_event(json.dumps(payload))

    assert event.kind == EventKind.MEDIA_ADDED
    assert event.item.media_type == "Episode"
    assert event.item.name == "Foundation"
    assert event.item.episode_number == 2
    assert event.item.season_number == 1
    assert event.buffer_key == "series-1_season-1"


def test_parse_notification_test_event():
    payload = {
        "Title": "Test",
        "Event": "system.notificationtest",
        "Server": {"Name": "Home", "Version": "4.8.0.80"},
    }

    event = parse_emby_event(json.dumps(payload))

    assert event.kind == EventKind.TEST
    assert event.server.name == "Home"


def test_unsupported_event_is_skipped():
    payload = {"Title": "Other", "Event": "library.deleted", "Server": {"Name": "Home"}}

    event = parse_emby_event(json.dumps(payload))

    assert event.kind == EventKind.SKIP
    assert "Unsupported event type" in event.reason
