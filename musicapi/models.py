from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Song:
    id: str
    title: str
    youtube_id: str | None = None
    youtube_url: str | None = None
    spotify_id: str | None = None
    spotify_url: str | None = None
    duration: int | None = None
    thumbnail: str | None = None
    audio_url: str | None = None
    audio_headers: dict[str, Any] | None = None
    audio_expires_at: datetime | None = None
    cache_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_api_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.title,
            "title": self.title,
            "youtube_id": self.youtube_id,
            "youtube_url": self.youtube_url,
            "spotify_id": self.spotify_id,
            "spotify_url": self.spotify_url,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "audio_url": self.audio_url,
            "audio_headers": self.audio_headers,
            "audio_expires_at": self.audio_expires_at.isoformat() if self.audio_expires_at else None,
            "cache_expires_at": self.cache_expires_at.isoformat() if self.cache_expires_at else None,
        }
