from __future__ import annotations

from datetime import datetime

from emby_notifier.domain.events import MediaItem, ServerInfo
from emby_notifier.domain.media import MediaDetail


class MediaEnricher:
    def __init__(self, tmdb_client):
        self.tmdb = tmdb_client

    def enrich(self, item: MediaItem, server: ServerInfo) -> MediaDetail:
        if item.media_type == "Movie":
            return self._enrich_movie(item, server)
        if item.media_type == "Episode":
            return self._enrich_episode(item, server)
        raise ValueError(f"Unsupported media type: {item.media_type}")

    def _enrich_movie(self, item: MediaItem, server: ServerInfo) -> MediaDetail:
        tmdb_id = item.provider_ids.get("Tmdb") or self._find_tmdb_id(item)
        details = self.tmdb.get_movie_details(tmdb_id)
        return MediaDetail(
            server_type=server.server_type,
            server_name=server.name,
            server_url=server.url,
            media_name=details.get("title", item.name),
            media_type="Movie",
            media_rating=details.get("vote_average", 0),
            media_rel=details.get("release_date", ""),
            media_intro=details.get("overview", ""),
            media_tmdburl=f"https://www.themoviedb.org/movie/{tmdb_id}?language=zh-CN",
            media_poster=self._image_url(details.get("poster_path")),
            media_backdrop=self._image_url(details.get("backdrop_path")),
        )

    def _enrich_episode(self, item: MediaItem, server: ServerInfo) -> MediaDetail:
        tmdb_id = self._find_tmdb_id(item)
        season_number = item.season_number or 0
        episode_number = item.episode_number or 0
        details = self.tmdb.get_tv_episode_details(tmdb_id, season_number, episode_number)
        season_details = None

        air_date = details.get("air_date")
        if air_date is None:
            season_details = self.tmdb.get_tv_season_details(tmdb_id, season_number)
            air_date = season_details.get("air_date") or str(datetime.now().year)

        if season_details is None:
            season_details = self.tmdb.get_tv_season_details(tmdb_id, season_number)

        poster = self._image_url(season_details.get("poster_path"))
        still = self._image_url(details.get("still_path")) or poster

        return MediaDetail(
            server_type=server.server_type,
            server_name=server.name,
            server_url=server.url,
            media_name=item.name,
            media_type="Episode",
            media_rating=details.get("vote_average", 0),
            media_rel=air_date,
            media_intro=details.get("overview", ""),
            media_tmdburl=f"https://www.themoviedb.org/tv/{tmdb_id}?language=zh-CN",
            media_poster=poster,
            media_still=still,
            tv_season=details.get("season_number", season_number),
            tv_episode=details.get("episode_number", episode_number),
            tv_episode_name=details.get("name", ""),
        )

    def _find_tmdb_id(self, item: MediaItem) -> str:
        results = self.tmdb.search_media(item.media_type, item.name, item.premiere_year)
        if not results:
            raise ValueError(f"No TMDB results found for {item.name}")

        return str(results[0]["id"])

    def _image_url(self, path: str | None) -> str:
        if not path:
            return ""
        return f"{self.tmdb.image_domain}/t/p/w500{path}"
