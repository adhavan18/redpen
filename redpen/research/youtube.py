"""youtube search + transcripts without an api key (yt-dlp search, youtube-transcript-api).

transcripts are what make videos usable inside a 45 minute lesson: instead of "watch this
20 minute video" the lesson can say "watch 3:10-6:40", the part that teaches the objective.
"""

import re
from concurrent.futures import ThreadPoolExecutor

import httpx

from .. import config

YDL_BASE = {"quiet": True, "no_warnings": True, "skip_download": True, "ignore_no_formats_error": True,
            "socket_timeout": 15}


def search(query: str, n: int = 6) -> list[dict]:
    import yt_dlp

    with yt_dlp.YoutubeDL(YDL_BASE | {"extract_flat": True}) as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    out = []
    for e in info.get("entries") or []:
        if not e or not e.get("id"):
            continue
        out.append({
            "video_id": e["id"],
            "title": e.get("title") or "",
            "channel": e.get("channel") or e.get("uploader") or "",
            "duration": int(e.get("duration") or 0),
            "views": int(e.get("view_count") or 0),
            "url": f"https://www.youtube.com/watch?v={e['id']}",
        })
    return out


def _transcript_api(video_id: str) -> list[dict]:
    from youtube_transcript_api import YouTubeTranscriptApi

    if hasattr(YouTubeTranscriptApi, "fetch") and not isinstance(
            getattr(YouTubeTranscriptApi, "fetch"), staticmethod):
        try:
            fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US", "en-GB"])
            return [{"start": float(s.start), "dur": float(s.duration), "text": s.text} for s in fetched]
        except TypeError:
            pass
    rows = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])  # old api
    return [{"start": float(r["start"]), "dur": float(r["duration"]), "text": r["text"]} for r in rows]


def _transcript_ytdlp(video_id: str) -> tuple[list[dict], dict]:
    """fallback: read caption track urls from the video's metadata and download json3 captions."""
    import yt_dlp

    with yt_dlp.YoutubeDL(YDL_BASE) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    meta = {"chapters": [{"title": c.get("title"), "start": c.get("start_time")} for c in info.get("chapters") or []],
            "upload_date": info.get("upload_date"), "description": (info.get("description") or "")[:600]}
    tracks = {}
    for src in (info.get("subtitles") or {}, info.get("automatic_captions") or {}):
        for lang in ("en", "en-US", "en-GB", "en-orig"):
            if lang in src and not tracks:
                tracks = {f["ext"]: f["url"] for f in src[lang] if f.get("url")}
    if "json3" not in tracks:
        return [], meta
    r = httpx.get(tracks["json3"], timeout=config.HTTP_TIMEOUT)
    r.raise_for_status()
    rows = []
    for ev in r.json().get("events", []):
        text = "".join(s.get("utf8", "") for s in ev.get("segs") or []).strip()
        if text:
            rows.append({"start": ev.get("tStartMs", 0) / 1000, "dur": ev.get("dDurationMs", 0) / 1000, "text": text})
    return rows, meta


def transcript(video_id: str) -> tuple[list[dict], dict, str | None]:
    """returns (lines, metadata, error). never raises."""
    meta: dict = {}
    try:
        return _transcript_api(video_id), meta, None
    except Exception as e:  # noqa: BLE001
        first = f"{type(e).__name__}"
    try:
        rows, meta = _transcript_ytdlp(video_id)
        if rows:
            return rows, meta, None
        return [], meta, f"no english captions ({first})"
    except Exception as e:  # noqa: BLE001
        return [], meta, f"{first}; yt-dlp: {type(e).__name__}"


def windows(lines: list[dict], size: float = 45.0) -> list[dict]:
    """group caption lines into ~45s windows for retrieval."""
    out, cur, start = [], [], None
    for ln in lines:
        if start is None:
            start = ln["start"]
        cur.append(re.sub(r"\s+", " ", ln["text"].replace("\n", " ")))
        end = ln["start"] + ln["dur"]
        if end - start >= size:
            out.append({"start": round(start, 1), "end": round(end, 1), "text": " ".join(cur)})
            cur, start = [], None
    if cur and start is not None:
        out.append({"start": round(start, 1), "end": round(lines[-1]["start"] + lines[-1]["dur"], 1),
                    "text": " ".join(cur)})
    return out


def enrich(videos: list[dict], workers: int = 4) -> list[dict]:
    def one(v):
        lines, meta, err = transcript(v["video_id"])
        return v | {"windows": windows(lines) if lines else [], "transcript_error": err,
                    "chapters": meta.get("chapters", []), "upload_date": meta.get("upload_date")}

    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, videos))


def fmt_ts(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def embed_url(video_id: str, start: float | None = None) -> str:
    return f"https://www.youtube.com/watch?v={video_id}" + (f"&t={int(start)}s" if start else "")


__all__ = ["search", "enrich", "transcript", "windows", "fmt_ts", "embed_url"]
