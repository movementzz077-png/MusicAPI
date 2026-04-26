from urllib.parse import parse_qs, unquote, urlparse


def normalize_query(query: str) -> str:
    return unquote(query).strip()


def normalize_alias(query: str) -> str:
    return normalize_query(query).lower()


def clean_url(url: str) -> str:
    parsed = urlparse(normalize_query(url))
    if not parsed.scheme:
        return normalize_query(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    query = parse_qs(parsed.query)

    if is_youtube_url(url):
        video_id = extract_youtube_id(url)
        return f"https://www.youtube.com/watch?v={video_id}" if video_id else normalize_query(url)

    if is_spotify_url(url):
        spotify_id = extract_spotify_id(url)
        return f"https://open.spotify.com/track/{spotify_id}" if spotify_id else normalize_query(url)

    kept_query = ""
    if query:
        kept_query = "?" + "&".join(f"{key}={values[0]}" for key, values in sorted(query.items()))
    return f"{scheme}://{netloc}{path}{kept_query}"


def is_youtube_url(value: str) -> bool:
    host = urlparse(normalize_query(value)).netloc.lower()
    return "youtube.com" in host or "youtu.be" in host


def is_spotify_url(value: str) -> bool:
    host = urlparse(normalize_query(value)).netloc.lower()
    return "spotify.com" in host


def extract_youtube_id(value: str) -> str | None:
    parsed = urlparse(normalize_query(value))
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        return parsed.path.strip("/") or None
    if "youtube.com" in host:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith("/shorts/") or parsed.path.startswith("/embed/"):
            return parsed.path.split("/")[2] if len(parsed.path.split("/")) > 2 else None
    return None


def extract_spotify_id(value: str) -> str | None:
    parsed = urlparse(normalize_query(value))
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "track":
        return parts[1]
    return None
