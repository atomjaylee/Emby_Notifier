from emby_notifier.services.emby_metadata import EmbyTechnicalEnricher


class FakeEmbyClient:
    def __init__(self, item):
        self.item = item
        self.item_ids = []

    def get_item(self, item_id):
        self.item_ids.append(item_id)
        return self.item


def test_emby_technical_enricher_extracts_high_value_fields():
    item = {
        "Path": "/media/[ADWeb] Dune.2021.2160p.DV.HDR.mkv",
        "Size": 19971597926,
        "MediaSources": [
            {
                "Size": 19971597926,
                "Path": "/media/[ADWeb] Dune.2021.2160p.DV.HDR.mkv",
                "MediaStreams": [
                    {"Type": "Video", "Width": 3840, "Height": 2160, "VideoRange": "DOVI"},
                    {"Type": "Subtitle", "Language": "chi", "Codec": "ass", "DisplayTitle": "简中特效 ASS"},
                    {"Type": "Subtitle", "Language": "eng", "Codec": "srt", "DisplayTitle": "English"},
                ],
            }
        ],
    }

    info = EmbyTechnicalEnricher(FakeEmbyClient(item)).get_info("movie-1")

    assert info.quality == "4K"
    assert info.dynamic_range == "Dolby Vision"
    assert info.subtitle == "简中特效"
    assert info.release_group == "ADWeb"
    assert info.size_gb == 18.6


def test_emby_technical_enricher_prefers_special_chinese_subtitle():
    item = {
        "Path": "/media/Foundation.S01E02-HHWEB.mkv",
        "MediaSources": [
            {
                "Size": 3672198840,
                "MediaStreams": [
                    {"Type": "Video", "Width": 1920, "Height": 1080, "VideoRange": "SDR"},
                    {"Type": "Subtitle", "Language": "zho", "Codec": "srt", "DisplayTitle": "简中"},
                    {"Type": "Subtitle", "Language": "zho", "Codec": "ass", "DisplayTitle": "简中特效"},
                ],
            }
        ],
    }

    info = EmbyTechnicalEnricher(FakeEmbyClient(item)).get_info("episode-1")

    assert info.quality == "1080p"
    assert info.dynamic_range == "SDR"
    assert info.subtitle == "简中特效"
    assert info.release_group == "HHWEB"
    assert info.size_gb == 3.42
