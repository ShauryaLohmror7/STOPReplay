"""Hacker News adapter — public, keyless search via the official Algolia REST API.

Endpoint: https://hn.algolia.com/api/v1/search
Discovers Show HN posts, stories, and comments by or referencing the target
person or their company/projects.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

import httpx

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftFact, DraftSource, ResearchRequest

_HN_API_URL = "https://hn.algolia.com/api/v1/search"
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


def _clean_text(html_text: str | None, max_len: int = 240) -> str:
    if not html_text:
        return ""
    text = _TAG_STRIP_RE.sub(" ", html_text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len - 3] + "..." if len(text) > max_len else text


def _parse_created_at(ts: Any) -> date | None:
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).date()
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


class HackerNewsAdapter(CollectionAdapter):
    name = "hackernews"

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 15.0):
        self._client = client
        self.timeout = timeout

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        out = CollectionOutput()
        query = request.query or request.subject
        if not query:
            out.retrieval_failures.append({"error": "no query provided for Hacker News search"})
            return out

        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            params = {
                "query": query,
                "hitsPerPage": request.limit or 5,
                "tags": "(story,comment)",
            }
            resp = client.get(_HN_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            out.retrieval_failures.append({"query": query, "error": f"{type(exc).__name__}: {exc}"})
            return out
        finally:
            if self._client is None:
                client.close()

        hits = data.get("hits", [])
        if not hits:
            return out

        today = date.today()
        for hit in hits:
            obj_id = str(hit.get("objectID") or "")
            if not obj_id:
                continue

            author = hit.get("author") or "unknown"
            title = hit.get("title") or hit.get("story_title") or ""
            text_body = hit.get("comment_text") or hit.get("story_text") or title or ""
            clean_body = _clean_text(text_body, max_len=300)
            story_url = hit.get("url") or hit.get("story_url")
            hn_item_url = f"https://news.ycombinator.com/item?id={obj_id}"
            item_date = _parse_created_at(hit.get("created_at_i") or hit.get("created_at")) or today

            is_story = bool(hit.get("title"))
            locator = f"Hacker News story: {title}" if is_story else f"Hacker News comment on item {obj_id}"

            # Register HN source
            out.sources.append(DraftSource(
                source_ref=hn_item_url,
                origin="social_post",
                url=hn_item_url,
                publisher="Hacker News",
                locator=locator,
                excerpt=clean_body or f"HN item {obj_id} by {author}",
                observed_on=item_date,
                retrieved_on=today
            ))

            # Emit structured facts
            if is_story and title:
                out.facts.append(DraftFact(
                    subject=request.subject,
                    claim=f"hn_submission: '{_clean_text(title, 120)}' by {author}",
                    category="project",
                    source_ref=hn_item_url,
                    confidence=0.75,
                    assertable=True,
                    assertable_why=f"Hacker News submission by or concerning target",
                    sensitivity="public"
                ))
            elif clean_body:
                out.facts.append(DraftFact(
                    subject=request.subject,
                    claim=f"hn_comment: '{_clean_text(clean_body, 160)}' by {author}",
                    category="other",
                    source_ref=hn_item_url,
                    confidence=0.7,
                    assertable=True,
                    assertable_why="public comment on Hacker News",
                    sensitivity="public"
                ))

        return out
