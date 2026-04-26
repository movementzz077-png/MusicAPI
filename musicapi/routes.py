import logging
import re
from urllib.parse import quote

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from musicapi.cache import MusicCache
from musicapi.config import ROOT_DIR, get_settings
from musicapi.database import db_session, init_db
from musicapi.services import AudioUnavailableError, MusicService, NotFoundError

LOGGER = logging.getLogger(__name__)

app = FastAPI(
    title="MusicAPI",
    description="API local para buscar músicas por nome, YouTube ou Spotify.",
    version="1.0.0",
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")
templates = Jinja2Templates(directory=ROOT_DIR / "templates")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def get_service():
    with db_session() as conn:
        yield MusicService(MusicCache(conn))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/prepare/{query:path}")
def prepare_song(query: str, service: MusicService = Depends(get_service)):
    try:
        song_id = service.prepare(query)
        return {"id": song_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("Prepare failed")
        raise HTTPException(status_code=502, detail=f"Não foi possível preparar a música: {exc}") from exc


@app.get("/api/fetch/{song_id}")
def fetch_song(song_id: str, service: MusicService = Depends(get_service)):
    try:
        return service.fetch(song_id).to_api_dict()
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("Fetch failed")
        raise HTTPException(status_code=502, detail=f"Não foi possível buscar dados da música: {exc}") from exc


@app.get("/api/audio/{song_id}")
async def stream_audio(
    song_id: str,
    request: Request,
    service: MusicService = Depends(get_service),
):
    try:
        song = service.fetch(song_id)
        audio_url = song.audio_url
        if not audio_url:
            raise AudioUnavailableError("Áudio indisponível para esta música no momento.")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AudioUnavailableError as exc:
        return JSONResponse(status_code=409, content={"error": str(exc), "song_id": song_id})

    upstream_headers = dict(song.audio_headers or {})
    if range_header := request.headers.get("range"):
        upstream_headers["Range"] = range_header

    client = httpx.AsyncClient(follow_redirects=True, timeout=None)
    try:
        upstream_request = client.build_request("GET", audio_url, headers=upstream_headers)
        upstream = await client.send(upstream_request, stream=True)
    except Exception as exc:
        await client.aclose()
        LOGGER.warning("Audio stream failed for %s: %s", song_id, exc)
        return JSONResponse(
            status_code=502,
            content={"error": "Não foi possível abrir o stream de áudio.", "song_id": song_id},
        )

    async def iterator():
        try:
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            except httpx.HTTPError as exc:
                LOGGER.warning("Audio stream interrupted for %s: %s", song_id, exc)
        finally:
            await upstream.aclose()
            await client.aclose()

    content_type = upstream.headers.get("content-type", "audio/mpeg")
    if _is_hls_response(audio_url, content_type):
        body = await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        return _hls_or_media_response(body, song_id)

    response_headers = {}
    for header in ("accept-ranges", "content-length", "content-range"):
        if value := upstream.headers.get(header):
            response_headers[header] = value
    return StreamingResponse(
        iterator(),
        media_type=content_type,
        status_code=upstream.status_code,
        headers=response_headers,
    )


@app.get("/api/audio/{song_id}/proxy")
async def proxy_audio_url(
    song_id: str,
    url: str,
    request: Request,
    service: MusicService = Depends(get_service),
):
    try:
        song = service.fetch(song_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    target_url = url
    upstream_headers = dict(song.audio_headers or {})
    if range_header := request.headers.get("range"):
        upstream_headers["Range"] = range_header

    client = httpx.AsyncClient(follow_redirects=True, timeout=None)
    try:
        upstream_request = client.build_request("GET", target_url, headers=upstream_headers)
        upstream = await client.send(upstream_request, stream=True)
    except Exception as exc:
        await client.aclose()
        LOGGER.warning("Audio proxy failed for %s: %s", song_id, exc)
        return JSONResponse(
            status_code=502,
            content={"error": "Não foi possível buscar o trecho de áudio.", "song_id": song_id},
        )

    content_type = upstream.headers.get("content-type", "application/octet-stream")
    if _is_hls_response(target_url, content_type):
        body = await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        return _hls_or_media_response(body, song_id)

    async def iterator():
        try:
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            except httpx.HTTPError as exc:
                LOGGER.warning("Audio proxy interrupted for %s: %s", song_id, exc)
        finally:
            await upstream.aclose()
            await client.aclose()

    response_headers = {}
    for header in ("accept-ranges", "content-length", "content-range"):
        if value := upstream.headers.get(header):
            response_headers[header] = value

    return StreamingResponse(
        iterator(),
        media_type=content_type,
        status_code=upstream.status_code,
        headers=response_headers,
    )


@app.get("/api/debug/audio/{song_id}")
async def debug_audio(song_id: str, service: MusicService = Depends(get_service)):
    try:
        song = service.fetch(song_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not song.audio_url:
        return {"song_id": song_id, "ok": False, "error": "audio_url ausente"}

    headers = dict(song.audio_headers or {})
    client = httpx.AsyncClient(follow_redirects=True, timeout=30)
    try:
        response = await client.get(song.audio_url, headers=headers)
        content_type = response.headers.get("content-type")
        body_start = response.content[:300].decode("utf-8", errors="replace")
        result = {
            "song_id": song_id,
            "ok": response.status_code < 400,
            "status_code": response.status_code,
            "content_type": content_type,
            "is_hls": _is_hls_response(song.audio_url, content_type),
            "playlist_is_rewritten": "/api/audio/" in _rewrite_hls_playlist(
                response.text, song_id
            )
            if response.content.lstrip().startswith(b"#EXTM3U")
            else False,
            "body_start": body_start,
        }
        if response.content.lstrip().startswith(b"#EXTM3U"):
            playlist = _rewrite_hls_playlist(response.text, song_id)
            first_proxy = next(
                (line for line in playlist.splitlines() if line.startswith("/api/audio/")),
                None,
            )
            result["first_proxy_url"] = first_proxy
            if first_proxy:
                segment_url = first_proxy.split("url=", 1)[1]
                segment_response = await client.get(segment_url)
                result["first_segment_status_code"] = segment_response.status_code
                result["first_segment_content_type"] = segment_response.headers.get("content-type")
                result["first_segment_size"] = len(segment_response.content)
        return result
    except Exception as exc:
        LOGGER.exception("Audio debug failed for %s", song_id)
        return {"song_id": song_id, "ok": False, "error": str(exc)}
    finally:
        await client.aclose()


def _is_hls_response(url: str, content_type: str | None) -> bool:
    media_type = (content_type or "").lower()
    return ".m3u8" in url.lower() or "mpegurl" in media_type or "application/vnd.apple" in media_type


def _rewrite_hls_playlist(playlist: str, song_id: str) -> str:
    def proxied(target: str) -> str:
        return f"/api/audio/{song_id}/proxy?url={quote(target, safe='')}"

    rewritten_lines = []
    for line in playlist.splitlines():
        stripped = line.strip()
        if stripped.startswith("http://") or stripped.startswith("https://"):
            rewritten_lines.append(proxied(stripped))
            continue
        line = re.sub(
            r'URI="(https?://[^"]+)"',
            lambda match: f'URI="{proxied(match.group(1))}"',
            line,
        )
        rewritten_lines.append(line)
    return "\n".join(rewritten_lines) + "\n"


def _hls_or_media_response(body: bytes, song_id: str) -> Response:
    if body.lstrip().startswith(b"#EXTM3U"):
        playlist = _rewrite_hls_playlist(body.decode("utf-8", errors="replace"), song_id)
        return Response(
            content=playlist,
            media_type="application/vnd.apple.mpegurl",
            headers={"cache-control": "no-store"},
        )
    return Response(
        content=body,
        media_type="video/mp2t",
        headers={"cache-control": "no-store"},
    )
