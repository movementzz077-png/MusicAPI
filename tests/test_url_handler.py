from musicapi.url_handler import clean_url, extract_spotify_id, extract_youtube_id, normalize_alias


def test_clean_youtube_url_removes_extra_params():
    url = "https://www.youtube.com/watch?v=abc123&utm_source=test&list=playlist"
    assert clean_url(url) == "https://www.youtube.com/watch?v=abc123"


def test_extract_youtube_short_url():
    assert extract_youtube_id("https://youtu.be/abc123?t=10") == "abc123"


def test_extract_spotify_track_url():
    url = "https://open.spotify.com/track/7ouMYWpwJ422jRcDASZB7P?si=value"
    assert extract_spotify_id(url) == "7ouMYWpwJ422jRcDASZB7P"


def test_normalize_alias_is_case_insensitive():
    assert normalize_alias("  One More Time  ") == "one more time"
