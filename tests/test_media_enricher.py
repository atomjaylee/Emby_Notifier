from emby_notifier.domain.events import MediaItem, ServerInfo
from emby_notifier.services.media_enricher import MediaEnricher


class FakeTMDB:
    def __init__(self):
        self.image_domain = "https://image.tmdb.org"

    def search_media(self, media_type, name, year):
        return [{"id": "93740", "original_name": name, "first_air_date": f"{year}-01-01"}]

    def get_movie_details(self, tmdb_id):
        return {
            "title": "Dune",
            "vote_average": 8.1,
            "release_date": "2021-09-15",
            "overview": "Desert power.",
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
        }

    def get_tv_episode_details(self, tmdb_id, season_number, episode_number):
        return {
            "vote_average": 7.5,
            "air_date": None,
            "overview": "The empire shifts.",
            "season_number": season_number,
            "episode_number": episode_number,
            "name": "Preparing to Live",
            "still_path": None,
        }

    def get_tv_details(self, tmdb_id):
        return {"number_of_seasons": 2}

    def get_tv_season_details(self, tmdb_id, season_number):
        return {
            "air_date": "2023-07-14",
            "poster_path": "/season.jpg",
            "episodes": [{"episode_number": number} for number in range(1, 41)],
        }


def server():
    return ServerInfo(name="Home", version="4.8.0.80", url="https://emby.media", server_type="Emby")


def test_enrich_movie_uses_existing_tmdb_id():
    item = MediaItem(
        media_type="Movie",
        name="Dune",
        premiere_year=2021,
        provider_ids={"Tmdb": "438631"},
    )

    detail = MediaEnricher(FakeTMDB()).enrich(item, server())

    assert detail.media_name == "Dune"
    assert detail.media_type == "Movie"
    assert detail.media_poster == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert detail.media_backdrop == "https://image.tmdb.org/t/p/w500/backdrop.jpg"


def test_enrich_episode_uses_tmdb_search_and_falls_back_to_season_data():
    item = MediaItem(
        media_type="Episode",
        name="Foundation",
        premiere_year=2023,
        provider_ids={"Tvdb": "123"},
        season_number=1,
        episode_number=2,
    )

    detail = MediaEnricher(FakeTMDB()).enrich(item, server())

    assert detail.media_name == "Foundation"
    assert detail.media_type == "Episode"
    assert detail.media_rel == "2023-07-14"
    assert detail.media_still == "https://image.tmdb.org/t/p/w500/season.jpg"
    assert detail.tv_season_episode_count == 40
    assert detail.tv_total_seasons == 2
