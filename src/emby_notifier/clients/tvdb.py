from __future__ import annotations

import requests


class TVDBClientError(RuntimeError):
    pass


class TVDBClient:
    def __init__(self, api_key: str, timeout: int = 8):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.base_url = "https://api4.thetvdb.com/v4"
        self._token: str | None = None

    def login(self) -> str:
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={"apikey": self.api_key},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TVDBClientError(f"TVDB login failed: {exc}") from exc
        self._token = response.json()["data"]["token"]
        return self._token

    def get_series_id_by_episode_id(self, episode_id: str | int) -> int:
        data = self._get(f"/episodes/{episode_id}")
        return data["data"]["seriesId"]

    def _get(self, path: str) -> dict:
        token = self._token or self.login()
        try:
            response = self.session.get(
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TVDBClientError(f"TVDB request failed for {path}: {exc}") from exc
        return response.json()
