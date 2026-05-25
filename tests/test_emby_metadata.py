from emby_notifier.services.emby_metadata import EmbyTechnicalEnricher


class FakeEmbyClient:
    def __init__(self, item):
        self.item = item
        self.item_ids = []

    def get_item(self, item_id):
        self.item_ids.append(item_id)
        return self.item


class FakeFallbackEmbyClient:
    def __init__(self, item):
        self.item = item
        self.item_ids = []
        self.tmdb_ids = []

    def get_item(self, item_id):
        self.item_ids.append(item_id)
        raise RuntimeError("not found")

    def find_item_by_tmdb_id(self, tmdb_id, preferred_item_id=None):
        self.tmdb_ids.append((tmdb_id, preferred_item_id))
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
    assert info.size_gb == 3.42


def test_emby_technical_enricher_does_not_treat_ass_format_as_special_subtitle():
    item = {
        "Path": "/media/AI.S01E05.mkv",
        "MediaSources": [
            {
                "Size": 3578537805,
                "MediaStreams": [
                    {"Type": "Video", "Width": 1920, "Height": 1080, "VideoRange": "SDR"},
                    {
                        "Type": "Subtitle",
                        "Language": "chi",
                        "Codec": "ass",
                        "DisplayTitle": "Chinese Simplified (默认 ASS)",
                        "Title": "chs",
                    },
                ],
            }
        ],
    }

    info = EmbyTechnicalEnricher(FakeEmbyClient(item)).get_info("episode-5")

    assert info.subtitle == "简中"


def test_emby_technical_enricher_marks_hard_subtitle_only_with_explicit_hint():
    item = {
        "Path": "/media/Movie.2024.1080p.HardSub.mkv",
        "MediaSources": [
            {
                "Name": "Movie.2024.1080p.内嵌中字.mkv",
                "MediaStreams": [
                    {"Type": "Video", "Width": 1920, "Height": 1080, "VideoRange": "SDR"},
                ],
            }
        ],
    }

    info = EmbyTechnicalEnricher(FakeEmbyClient(item)).get_info("movie-2")

    assert info.subtitle == "硬字幕"


def test_emby_technical_enricher_reports_no_independent_subtitle_without_subtitle_streams():
    item = {
        "Path": "/media/Dont.Say.a.Word.2001.2160p.WEB-DL.H265.mkv",
        "MediaSources": [
            {
                "Name": "Dont.Say.a.Word.2001.2160p.WEB-DL.H265.mkv",
                "MediaStreams": [
                    {"Type": "Video", "Width": 3840, "Height": 1632, "VideoRange": "SDR"},
                    {"Type": "Audio", "Language": "chi", "DisplayTitle": "Chinese Simplified DTS 5.1"},
                ],
            }
        ],
    }

    info = EmbyTechnicalEnricher(FakeEmbyClient(item)).get_info("movie-3")

    assert info.subtitle == "无独立字幕"


def test_emby_technical_enricher_reads_item_level_media_streams_when_source_has_none():
    item = {
        "Path": "/media/Fearless.2006.1080p.mkv",
        "MediaSources": [
            {
                "Size": 8589934592,
                "Path": "/media/Fearless.2006.1080p.mkv",
            }
        ],
        "MediaStreams": [
            {"Type": "Video", "Width": 1920, "Height": 1080, "VideoRange": "SDR"},
            {"Type": "Subtitle", "Language": "chi", "Codec": "srt", "DisplayTitle": "简中 SRT"},
        ],
    }

    info = EmbyTechnicalEnricher(FakeEmbyClient(item)).get_info("movie-4")

    assert info.quality == "1080p"
    assert info.dynamic_range == "SDR"
    assert info.subtitle == "简中"
    assert info.size_gb == 8


def test_emby_technical_enricher_falls_back_to_tmdb_id_lookup():
    item = {
        "Path": "/media/[ADWeb] Happening.2021.2160p.HDR.mkv",
        "MediaSources": [
            {
                "Size": 8589934592,
                "MediaStreams": [
                    {"Type": "Video", "Width": 3840, "Height": 2160, "VideoRange": "HDR10"},
                ],
            }
        ],
    }
    client = FakeFallbackEmbyClient(item)

    info = EmbyTechnicalEnricher(client).get_info("420180", tmdb_id="749643")

    assert client.item_ids == ["420180"]
    assert client.tmdb_ids == [("749643", "420180")]
    assert info.quality == "4K"
    assert info.dynamic_range == "HDR10"
    assert info.size_gb == 8
