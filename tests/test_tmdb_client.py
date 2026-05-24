from emby_notifier.clients.tmdb import TMDBClient


class FakeResponse:
    def __init__(self, payload=None):
        self.payload = payload or {"success": True}

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "headers": headers or {},
                "params": params or {},
                "timeout": timeout,
            }
        )
        return FakeResponse()


def test_tmdb_client_uses_api_key_param_for_v3_key():
    client = TMDBClient("0123456789abcdef0123456789abcdef", "https://image.tmdb.org")
    client.session = FakeSession()

    client.validate()

    call = client.session.calls[0]
    assert call["params"]["api_key"] == "0123456789abcdef0123456789abcdef"
    assert "Authorization" not in call["headers"]


def test_tmdb_client_uses_bearer_header_for_v4_token():
    client = TMDBClient("eyJ.header.payload", "https://image.tmdb.org")
    client.session = FakeSession()

    client.validate()

    call = client.session.calls[0]
    assert call["headers"]["Authorization"] == "Bearer eyJ.header.payload"
    assert "api_key" not in call["params"]
