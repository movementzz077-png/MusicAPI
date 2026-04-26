from contextlib import contextmanager
from pathlib import Path
import sqlite3

from musicapi.config import get_settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS songs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    youtube_id TEXT,
    youtube_url TEXT,
    spotify_id TEXT,
    spotify_url TEXT,
    duration INTEGER,
    thumbnail TEXT,
    audio_url TEXT,
    audio_headers TEXT,
    audio_expires_at TEXT,
    cache_expires_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_songs_youtube_id ON songs(youtube_id);
CREATE INDEX IF NOT EXISTS idx_songs_spotify_id ON songs(spotify_id);

CREATE TABLE IF NOT EXISTS aliases (
    alias TEXT PRIMARY KEY,
    song_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
);
"""


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    settings = get_settings()
    path = Path(db_path or settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(songs)").fetchall()}
        if "audio_headers" not in columns:
            conn.execute("ALTER TABLE songs ADD COLUMN audio_headers TEXT")


@contextmanager
def db_session(db_path: str | None = None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
