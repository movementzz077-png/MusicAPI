from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from musicapi.cache import MusicCache, utcnow
from musicapi.database import get_connection, init_db
from musicapi.models import Song


def test_create_and_fetch_song_from_cache():
    temp_dir = Path(__file__).parent / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    db_path = temp_dir / f"musicapi-test-{uuid4().hex}.sqlite3"

    init_db(str(db_path))
    conn = get_connection(str(db_path))
    cache = MusicCache(conn)

    song = Song(
        id="song-1",
        title="Test Track",
        youtube_id="yt-1",
        youtube_url="https://www.youtube.com/watch?v=yt-1",
        audio_url="https://example.com/audio",
        audio_headers={"User-Agent": "pytest"},
        audio_expires_at=utcnow() + timedelta(minutes=10),
        cache_expires_at=utcnow() + timedelta(days=1),
    )
    cache.save_song(song)
    cache.add_alias("Test Track", song.id)
    conn.commit()

    cached = cache.get_song("song-1")
    by_alias = cache.find_by_alias("test track")

    assert cached is not None
    assert cached.title == "Test Track"
    assert by_alias is not None
    assert by_alias.id == "song-1"
    assert cache.audio_url_is_valid(cached)
    conn.close()
