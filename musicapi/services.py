from datetime import timedelta
import logging
from uuid import uuid4

from musicapi.cache import MusicCache, utcnow
from musicapi.config import get_settings
from musicapi.models import Song
from musicapi.spotify_client import SpotifyClient, SpotifyMetadata
from musicapi.url_handler import (
    clean_url,
    extract_spotify_id,
    extract_youtube_id,
    is_spotify_url,
    is_youtube_url,
    normalize_query,
)
from musicapi.youtube import YouTubeClient, YouTubeMetadata

LOGGER = logging.getLogger(__name__)


class NotFoundError(Exception):
    pass


class AudioUnavailableError(Exception):
    pass


class MusicService:
    def __init__(
        self,
        cache: MusicCache,
        youtube: YouTubeClient | None = None,
        spotify: SpotifyClient | None = None,
    ) -> None:
        self.cache = cache
        self.youtube = youtube or YouTubeClient()
        self.spotify = spotify or SpotifyClient()
        self.settings = get_settings()

    def prepare(self, raw_query: str) -> str:
        query = clean_url(normalize_query(raw_query))
        if not query:
            raise ValueError("Informe uma música, URL do YouTube ou URL do Spotify.")

        cached = self.cache.find_by_alias(query)
        if cached and self.cache.cache_is_valid(cached):
            return cached.id

        youtube_id = extract_youtube_id(query) if is_youtube_url(query) else None
        spotify_id = extract_spotify_id(query) if is_spotify_url(query) else None
        cached_by_id = self.cache.find_by_external_id(youtube_id=youtube_id, spotify_id=spotify_id)
        if cached_by_id and self.cache.cache_is_valid(cached_by_id):
            self.cache.add_alias(query, cached_by_id.id)
            return cached_by_id.id

        spotify_meta = self.spotify.fetch(query) if (is_spotify_url(query) or self.spotify.available) else None
        youtube_query = self._youtube_query(query, spotify_meta)
        youtube_meta = self.youtube.fetch(youtube_query)

        existing = self.cache.find_by_external_id(
            youtube_id=youtube_meta.id,
            spotify_id=spotify_meta.id if spotify_meta else spotify_id,
        )
        song = self._build_song(existing.id if existing else str(uuid4()), youtube_meta, spotify_meta)
        saved = self.cache.save_song(song)
        self.cache.add_alias(query, saved.id)
        if spotify_meta:
            self.cache.add_alias(spotify_meta.url, saved.id)
        if youtube_meta.url:
            self.cache.add_alias(youtube_meta.url, saved.id)
        return saved.id

    def fetch(self, song_id: str) -> Song:
        song = self.cache.get_song(song_id)
        if not song:
            raise NotFoundError("Música não encontrada no cache.")

        if not self.cache.audio_url_is_valid(song):
            song = self._refresh_audio_url(song)
        return song

    def audio_url(self, song_id: str) -> str:
        song = self.fetch(song_id)
        if not song.audio_url:
            raise AudioUnavailableError("Áudio indisponível para esta música no momento.")
        return song.audio_url

    def _refresh_audio_url(self, song: Song) -> Song:
        if not song.youtube_url and not song.youtube_id:
            return song
        lookup = song.youtube_url or f"https://www.youtube.com/watch?v={song.youtube_id}"
        try:
            meta = self.youtube.fetch(lookup)
        except Exception as exc:
            LOGGER.warning("Could not refresh audio URL for %s: %s", song.id, exc)
            expired = Song(
                id=song.id,
                title=song.title,
                youtube_id=song.youtube_id,
                youtube_url=song.youtube_url,
                spotify_id=song.spotify_id,
                spotify_url=song.spotify_url,
                duration=song.duration,
                thumbnail=song.thumbnail,
                audio_url=None,
                audio_headers=None,
                audio_expires_at=None,
                cache_expires_at=song.cache_expires_at,
                created_at=song.created_at,
            )
            return self.cache.save_song(expired)

        refreshed = Song(
            id=song.id,
            title=meta.title or song.title,
            youtube_id=meta.id or song.youtube_id,
            youtube_url=meta.url or song.youtube_url,
            spotify_id=song.spotify_id,
            spotify_url=song.spotify_url,
            duration=meta.duration or song.duration,
            thumbnail=meta.thumbnail or song.thumbnail,
            audio_url=meta.audio_url,
            audio_headers=meta.audio_headers,
            audio_expires_at=utcnow() + timedelta(seconds=self.settings.audio_url_ttl_seconds),
            cache_expires_at=utcnow() + timedelta(seconds=self.settings.cache_ttl_seconds),
            created_at=song.created_at,
        )
        return self.cache.save_song(refreshed)

    def _build_song(
        self,
        song_id: str,
        youtube_meta: YouTubeMetadata,
        spotify_meta: SpotifyMetadata | None,
    ) -> Song:
        return Song(
            id=song_id,
            title=spotify_meta.title if spotify_meta else youtube_meta.title,
            youtube_id=youtube_meta.id,
            youtube_url=youtube_meta.url,
            spotify_id=spotify_meta.id if spotify_meta else None,
            spotify_url=spotify_meta.url if spotify_meta else None,
            duration=spotify_meta.duration if spotify_meta and spotify_meta.duration else youtube_meta.duration,
            thumbnail=spotify_meta.thumbnail if spotify_meta and spotify_meta.thumbnail else youtube_meta.thumbnail,
            audio_url=youtube_meta.audio_url,
            audio_headers=youtube_meta.audio_headers,
            audio_expires_at=utcnow() + timedelta(seconds=self.settings.audio_url_ttl_seconds),
            cache_expires_at=utcnow() + timedelta(seconds=self.settings.cache_ttl_seconds),
        )

    def _youtube_query(self, query: str, spotify_meta: SpotifyMetadata | None) -> str:
        if is_youtube_url(query):
            return query
        if spotify_meta:
            return f"{spotify_meta.title} audio"
        return query
