from emby_notifier.clients.emby import EmbyClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.requests = []

    def get(self, url, params=None, timeout=None):
        self.requests.append((url, params, timeout))
        return FakeResponse({"Items": [{"Id": "movie-1", "Name": "Dune"}]})


def test_get_item_uses_items_query_with_media_fields():
    client = EmbyClient("https://example.test", "secret", timeout=7)
    client.session = FakeSession()

    item = client.get_item("420180")

    assert item["Id"] == "movie-1"
    assert client.session.requests == [
        (
            "https://example.test/emby/Items",
            {
                "api_key": "secret",
                "Ids": "420180",
                "Fields": "MediaSources,Path,ProviderIds",
            },
            7,
        )
    ]


def test_find_item_by_tmdb_id_uses_provider_id_lookup():
    client = EmbyClient("https://example.test", "secret", timeout=7)
    client.session = FakeSession()

    item = client.find_item_by_tmdb_id("438631")

    assert item["Id"] == "movie-1"
    assert client.session.requests == [
        (
            "https://example.test/emby/Items",
            {
                "api_key": "secret",
                "Recursive": "true",
                "IncludeItemTypes": "Movie,Episode",
                "AnyProviderIdEquals": "tmdb.438631",
                "Fields": "MediaSources,Path,ProviderIds",
            },
            7,
        )
    ]


class MultiItemSession:
    def __init__(self):
        self.requests = []

    def get(self, url, params=None, timeout=None):
        self.requests.append((url, params, timeout))
        return FakeResponse({
            "Items": [
                {"Id": "90690", "Name": "正发生"},
                {"Id": "420180", "Name": "正发生"},
            ]
        })


def test_find_item_by_tmdb_id_prefers_matching_item_id():
    client = EmbyClient("https://example.test", "secret", timeout=7)
    client.session = MultiItemSession()

    item = client.find_item_by_tmdb_id("793998", preferred_item_id="420180")

    assert item["Id"] == "420180"
