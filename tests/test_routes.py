from datetime import timedelta

from fastapi.testclient import TestClient

from musicapi.cache import utcnow
from musicapi.models import Song
from musicapi.routes import app, get_service


class FakeService:
    def prepare(self, query: str) -> str:
        assert query
        return "song-1"

    def fetch(self, song_id: str) -> Song:
        return Song(
            id=song_id,
            title="Test Track",
            youtube_id="yt-1",
            youtube_url="https://www.youtube.com/watch?v=yt-1",
            spotify_id="sp-1",
            spotify_url="https://open.spotify.com/track/sp-1",
            duration=180,
            thumbnail="https://example.com/thumb.jpg",
            audio_url="https://example.com/audio.mp3",
            audio_expires_at=utcnow() + timedelta(minutes=10),
            cache_expires_at=utcnow() + timedelta(days=1),
        )

    def audio_url(self, song_id: str) -> str:
        return "https://example.com/audio.mp3"


def override_service():
    yield FakeService()


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_prepare_and_fetch_endpoints():
    app.dependency_overrides[get_service] = override_service
    try:
        with TestClient(app) as client:
            prepared = client.get("/api/prepare/Test%20Track")
            fetched = client.get("/api/fetch/song-1")
    finally:
        app.dependency_overrides.clear()

    assert prepared.status_code == 200
    assert prepared.json() == {"id": "song-1"}
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Test Track"
