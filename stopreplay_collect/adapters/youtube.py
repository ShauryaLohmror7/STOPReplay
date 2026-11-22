"""Preserve public YouTube caption text with language and time references."""
from __future__ import annotations

import re
from datetime import date
from math import isfinite
from urllib.parse import parse_qs, urlsplit
from xml.etree.ElementTree import ParseError

from requests import RequestException, Session
from youtube_transcript_api import YouTubeTranscriptApi, YouTubeTranscriptApiException

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftSource, ResearchRequest

_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
_DEFAULT_LANGUAGES = ("en", "en-US", "en-GB")


def _video_id(url: str) -> str | None:
    parsed = urlsplit(url)
    host = parsed.netloc.lower()
    if parsed.scheme != "https":
        return None
    if host == "youtu.be":
        candidate = parsed.path.removeprefix("/")
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"} and parsed.path == "/watch":
        values = parse_qs(parsed.query).get("v", [])
        candidate = values[0] if len(values) == 1 else ""
    else:
        return None
    return candidate if _VIDEO_ID.fullmatch(candidate) else None


class _CaptionSession(Session):
    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", 15)
        return super().request(method, url, **kwargs)


class YouTubeAdapter(CollectionAdapter):
    name = "youtube"

    def __init__(self, *, client: YouTubeTranscriptApi | None = None) -> None:
        self._client = client

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        output = CollectionOutput()
        urls = request.params.get("urls", [])
        if not urls:
            output.retrieval_failures.append({"error": "supply at least one public YouTube video URL"})
            return output

        languages = request.params.get("languages") or _DEFAULT_LANGUAGES
        with _CaptionSession() as session:
            session.trust_env = False
            client = self._client if self._client is not None else YouTubeTranscriptApi(http_client=session)
            seen = set()
            for url in urls[:request.limit]:
                try:
                    video_id = _video_id(url)
                except ValueError:
                    video_id = None
                if video_id is None:
                    output.retrieval_failures.append({"error": "expected a public HTTPS YouTube watch or share URL"})
                elif video_id not in seen:
                    seen.add(video_id)
                    self._collect_video(client, video_id, languages, output)
        return output

    def _collect_video(self, client, video_id, languages, output: CollectionOutput) -> None:
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            track = client.fetch(video_id, languages=languages)
        except (YouTubeTranscriptApiException, RequestException) as exc:
            output.retrieval_failures.append({"url": url, "error": type(exc).__name__})
            return
        except (ValueError, ParseError) as exc:
            output.extraction_failures.append({"url": url, "error": type(exc).__name__})
            return

        sources = []
        language = track.language_code
        caption_type = "auto-generated captions" if track.is_generated else "captions"
        for position, cue in enumerate(track, 1):
            if not cue.text.strip():
                continue
            end = cue.start + cue.duration
            if not all(isfinite(t) and t >= 0 for t in (cue.start, cue.duration, end)):
                output.extraction_failures.append({"url": url, "error": f"invalid timing for caption {position}"})
                continue
            start_ms = round(cue.start * 1000)
            end_ms = round(end * 1000)
            sources.append(DraftSource(
                source_ref=f"youtube:{video_id}:{language}:{start_ms}:{end_ms}:{position}",
                origin="public_talk", url=f"{url}&t={start_ms // 1000}s", publisher="YouTube",
                locator=f"{start_ms / 1000:.3f}s–{end_ms / 1000:.3f}s ({language}, {caption_type})",
                excerpt=cue.text.strip(), retrieved_on=date.today(),
            ))
        if not sources:
            output.extraction_failures.append({"url": url, "error": "YouTube returned no usable caption text"})
        output.sources.extend(sources)
