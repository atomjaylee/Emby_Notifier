from __future__ import annotations

import requests


class EmbyClientError(RuntimeError):
    pass


class EmbyClient:
    def __init__(self, server_url: str, api_key: str, timeout: int = 5):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def get_item(self, item_id: str) -> dict:
        try:
            response = self.session.get(
                f"{self.server_url}/emby/Items/{item_id}",
                params={"api_key": self.api_key},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise EmbyClientError(f"Emby item query failed for {item_id}: {exc}") from exc
        return response.json()
