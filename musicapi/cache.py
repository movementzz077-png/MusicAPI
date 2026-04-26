from datetime import datetime, timezone
import json
import sqlite3

from musicapi.models import Song
from musicapi.url_handler import normalize_alias


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def serialize_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def parse_json(value: str | None) -> dict | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def serialize_json(value: dict | None) -> str | None:
    return json.dumps(value) if value else None


def row_to_song(row: sqlite3.Row | None) -> Song | None:
    if row is None:
        return None
    return Song(
        id=row["id"],
        title=row["title"],
        youtube_id=row["youtube_id"],
        youtube_url=row["youtube_url"],
        spotify_id=row["spotify_id"],
        spotify_url=row["spotify_url"],
        duration=row["duration"],
        thumbnail=row["thumbnail"],
        audio_url=row["audio_url"],
        audio_headers=parse_json(row["audio_headers"]),
        audio_expires_at=parse_dt(row["audio_expires_at"]),
        cache_expires_at=parse_dt(row["cache_expires_at"]),
        created_at=parse_dt(row["created_at"]),
        updated_at=parse_dt(row["updated_at"]),
    )


class MusicCache:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_song(self, song_id: str) -> Song | None:
        row = self.conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
        return row_to_song(row)

    def find_by_alias(self, query: str) -> Song | None:
        alias = normalize_alias(query)
        row = self.conn.execute(
            """
            SELECT s.* FROM aliases a
            JOIN songs s ON s.id = a.song_id
            WHERE a.alias = ?
            """,
            (alias,),
        ).fetchone()
        return row_to_song(row)

    def find_by_external_id(
        self, youtube_id: str | None = None, spotify_id: str | None = None
    ) -> Song | None:
        if youtube_id:
            row = self.conn.execute("SELECT * FROM songs WHERE youtube_id = ?", (youtube_id,)).fetchone()
            if row:
                return row_to_song(row)
        if spotify_id:
            row = self.conn.execute("SELECT * FROM songs WHERE spotify_id = ?", (spotify_id,)).fetchone()
            if row:
                return row_to_song(row)
        return None

    def save_song(self, song: Song) -> Song:
        now = serialize_dt(utcnow())
        created = serialize_dt(song.created_at) or now
        self.conn.execute(
            """
            INSERT INTO songs (
                id, title, youtube_id, youtube_url, spotify_id, spotify_url, duration,
                thumbnail, audio_url, audio_headers, audio_expires_at, cache_expires_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                youtube_id = COALESCE(excluded.youtube_id, songs.youtube_id),
                youtube_url = COALESCE(excluded.youtube_url, songs.youtube_url),
                spotify_id = COALESCE(excluded.spotify_id, songs.spotify_id),
                spotify_url = COALESCE(excluded.spotify_url, songs.spotify_url),
                duration = COALESCE(excluded.duration, songs.duration),
                thumbnail = COALESCE(excluded.thumbnail, songs.thumbnail),
                audio_url = excluded.audio_url,
                audio_headers = excluded.audio_headers,
                audio_expires_at = excluded.audio_expires_at,
                cache_expires_at = excluded.cache_expires_at,
                updated_at = excluded.updated_at
            """,
            (
                song.id,
                song.title,
                song.youtube_id,
                song.youtube_url,
                song.spotify_id,
                song.spotify_url,
                song.duration,
                song.thumbnail,
                song.audio_url,
                serialize_json(song.audio_headers),
                serialize_dt(song.audio_expires_at),
                serialize_dt(song.cache_expires_at),
                created,
                now,
            ),
        )
        return self.get_song(song.id) or song

    def add_alias(self, query: str, song_id: str) -> None:
        self.conn.execute(
            """
            INSERT INTO aliases(alias, song_id, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(alias) DO UPDATE SET song_id = excluded.song_id
            """,
            (normalize_alias(query), song_id, serialize_dt(utcnow())),
        )

    def audio_url_is_valid(self, song: Song) -> bool:
        return bool(
            song.audio_url
            and song.audio_headers
            and song.audio_expires_at
            and song.audio_expires_at > utcnow()
        )

    def cache_is_valid(self, song: Song) -> bool:
        return bool(song.cache_expires_at and song.cache_expires_at > utcnow())
