from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL

from musicapi.config import get_settings

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class YouTubeMetadata:
    id: str | None
    url: str | None
    title: str
    duration: int | None
    thumbnail: str | None
    audio_url: str | None
    audio_headers: dict[str, Any] | None


class YouTubeClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "format": "bestaudio[protocol^=http]/bestaudio/best",
            "default_search": "ytsearch1",
        }
        if settings.ytdlp_cookies_file:
            cookies_path = Path(settings.ytdlp_cookies_file)
            if cookies_path.exists():
                self.base_options["cookiefile"] = str(cookies_path)
            else:
                LOGGER.warning("YTDLP_COOKIES_FILE does not exist: %s", cookies_path)

    def fetch(self, query: str, refresh_audio: bool = True) -> YouTubeMetadata:
        options = dict(self.base_options)
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(query, download=False)

        if info is None:
            raise RuntimeError("Nenhum resultado encontrado no YouTube.")

        if "entries" in info:
            entries = [entry for entry in info.get("entries") or [] if entry]
            if not entries:
                raise RuntimeError("Nenhum resultado encontrado no YouTube.")
            info = entries[0]

        video_id = info.get("id")
        webpage_url = info.get("webpage_url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else None)
        selected_audio = self._select_audio_format(info) if refresh_audio else {}
        audio_url = selected_audio.get("url")
        audio_headers = selected_audio.get("http_headers") or info.get("http_headers")

        return YouTubeMetadata(
            id=video_id,
            url=webpage_url,
            title=info.get("title") or "Música sem título",
            duration=info.get("duration"),
            thumbnail=info.get("thumbnail"),
            audio_url=audio_url,
            audio_headers=audio_headers,
        )

    def _select_audio_format(self, info: dict) -> dict:
        formats = info.get("formats") or []
        direct_formats = []
        for item in formats:
            url = item.get("url")
            protocol = (item.get("protocol") or "").lower()
            if not url or "m3u8" in protocol or ".m3u8" in url:
                continue
            if item.get("acodec") == "none":
                continue
            direct_formats.append(item)

        if direct_formats:
            audio_only = [item for item in direct_formats if item.get("vcodec") == "none"]
            candidates = audio_only or direct_formats
            return max(candidates, key=lambda item: item.get("abr") or item.get("tbr") or 0)

        return info if info.get("url") else {}
