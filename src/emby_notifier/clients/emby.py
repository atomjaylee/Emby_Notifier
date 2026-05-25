from __future__ import annotations

import requests


MEDIA_FIELDS = "MediaSources,MediaStreams,Path,ProviderIds"


class EmbyClientError(RuntimeError):
    pass


class EmbyClient:
    def __init__(self, server_url: str, api_key: str, timeout: int = 5):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def get_item(self, item_id: str) -> dict:
        data = self._get_json(
            "/emby/Items",
            {
                "api_key": self.api_key,
                "Ids": item_id,
                "Fields": MEDIA_FIELDS,
            },
            f"item {item_id}",
        )
        items = data.get("Items") or []
        if not items:
            raise EmbyClientError(f"Emby item not found for item {item_id}")
        return items[0]

    def find_item_by_tmdb_id(self, tmdb_id: str, preferred_item_id: str | None = None) -> dict:
        data = self._get_json(
            "/emby/Items",
            {
                "api_key": self.api_key,
                "Recursive": "true",
                "IncludeItemTypes": "Movie,Episode",
                "AnyProviderIdEquals": f"tmdb.{tmdb_id}",
                "Fields": MEDIA_FIELDS,
            },
            f"TMDB id {tmdb_id}",
        )
        items = data.get("Items") or []
        if not items:
            raise EmbyClientError(f"Emby item not found for TMDB id {tmdb_id}")
        if preferred_item_id is not None:
            for item in items:
                if str(item.get("Id")) == str(preferred_item_id):
                    return item
        return items[0]

    def _get_json(self, path: str, params: dict, label: str) -> dict:
        try:
            response = self.session.get(
                f"{self.server_url}{path}",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise EmbyClientError(f"Emby item query failed for {label}: {exc}") from exc
        return response.json()
