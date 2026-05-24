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
            },
            7,
        )
    ]
