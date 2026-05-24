from __future__ import annotations

import requests


class TMDBClientError(RuntimeError):
    pass


class TMDBClient:
    def __init__(self, api_token: str, image_domain: str, timeout: int = 8):
        self.image_domain = image_domain.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {api_token}",
        }
        self.base_url = "https://api.themoviedb.org/3"

    def validate(self) -> None:
        self._get("/authentication")

    def search_media(self, media_type: str, name: str, year: int) -> list[dict]:
        tmdb_type = _tmdb_media_type(media_type)
        params = {"query": name, "language": "zh-CN", "page": 1}
        if year != -1:
            params["year"] = year
        return self._get(f"/search/{tmdb_type}", params).get("results", [])

    def get_external_ids(self, media_type: str, tmdb_id: str | int) -> dict:
        tmdb_type = _tmdb_media_type(media_type)
        return self._get(f"/{tmdb_type}/{tmdb_id}/external_ids", {"language": "zh-CN"})

    def get_movie_details(self, tmdb_id: str | int) -> dict:
        return self._get(f"/movie/{tmdb_id}", {"language": "zh-CN"})

    def get_tv_episode_details(self, tmdb_id: str | int, season_number: int, episode_number: int) -> dict:
        return self._get(
            f"/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}",
            {"language": "zh-CN"},
        )

    def get_tv_season_details(self, tmdb_id: str | int, season_number: int) -> dict:
        return self._get(f"/tv/{tmdb_id}/season/{season_number}", {"language": "zh-CN"})

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            response = self.session.get(
                f"{self.base_url}{path}",
                headers=self.headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TMDBClientError(f"TMDB request failed for {path}: {exc}") from exc
        return response.json()


def _tmdb_media_type(media_type: str) -> str:
    return {"Movie": "movie", "Episode": "tv"}.get(media_type, media_type)
