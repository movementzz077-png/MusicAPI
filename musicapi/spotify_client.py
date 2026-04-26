from dataclasses import dataclass
import logging

from musicapi.config import get_settings
from musicapi.url_handler import extract_spotify_id

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SpotifyMetadata:
    id: str
    url: str
    title: str
    artist: str | None
    duration: int | None
    thumbnail: str | None


class SpotifyClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    @property
    def available(self) -> bool:
        return self.settings.spotify_enabled

    def client(self):
        if not self.available:
            return None
        if self._client is None:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials

            auth_manager = SpotifyClientCredentials(
                client_id=self.settings.spotify_client_id,
                client_secret=self.settings.spotify_client_secret,
            )
            self._client = spotipy.Spotify(auth_manager=auth_manager)
        return self._client

    def fetch(self, query: str) -> SpotifyMetadata | None:
        sp = self.client()
        if sp is None:
            return None

        try:
            spotify_id = extract_spotify_id(query)
            track = sp.track(spotify_id) if spotify_id else self._search_track(sp, query)
            if not track:
                return None
            artists = ", ".join(artist["name"] for artist in track.get("artists", []))
            images = track.get("album", {}).get("images", [])
            title = track.get("name") or "Música sem título"
            return SpotifyMetadata(
                id=track["id"],
                url=track.get("external_urls", {}).get("spotify", f"https://open.spotify.com/track/{track['id']}"),
                title=f"{title} - {artists}" if artists else title,
                artist=artists or None,
                duration=round((track.get("duration_ms") or 0) / 1000) or None,
                thumbnail=images[0]["url"] if images else None,
            )
        except Exception as exc:
            LOGGER.warning("Spotify lookup failed: %s", exc)
            return None

    def _search_track(self, sp, query: str) -> dict | None:
        result = sp.search(q=query, type="track", limit=1)
        items = result.get("tracks", {}).get("items", [])
        return items[0] if items else None
