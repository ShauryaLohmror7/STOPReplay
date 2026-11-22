"""Read explicit V2EX topics through Agent-Reach's unauthenticated REST path."""
from __future__ import annotations

import re
from contextlib import nullcontext
from datetime import date, datetime, timezone

import httpx

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftSource, ResearchRequest

_TOPICS_URL = "https://www.v2ex.com/api/topics/show.json"
_TOPIC_LINK = re.compile(r"https://(?:www\.)?v2ex\.com/t/([1-9][0-9]*)(?:[?#][^\s]*)?", re.IGNORECASE)


def _publication_date(timestamp: object) -> date | None:
    if not isinstance(timestamp, int):
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
    except (OSError, OverflowError, ValueError):
        return None


class AgentReachAdapter(CollectionAdapter):
    name = "agent-reach"

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._client = client

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        output = CollectionOutput()
        urls = request.params.get("urls", [])
        if not urls:
            output.retrieval_failures.append({"error": "supply at least one public V2EX topic URL"})
            return output

        context = nullcontext(self._client) if self._client is not None else httpx.Client(timeout=15)
        with context as client:
            for url in urls[:request.limit]:
                match = _TOPIC_LINK.fullmatch(url)
                if not match:
                    output.retrieval_failures.append({"error": "expected a public HTTPS V2EX topic URL"})
                    continue
                self._collect_topic(client, match[1], output)
        return output

    def _collect_topic(self, client: httpx.Client, topic_id: str, output: CollectionOutput) -> None:
        url = f"https://www.v2ex.com/t/{topic_id}"
        try:
            response = client.get(_TOPICS_URL, params={"id": topic_id}, follow_redirects=False)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            output.retrieval_failures.append({"url": url, "error": str(exc)})
            return

        try:
            topics = response.json()
            if topics == []:
                output.retrieval_failures.append({"url": url, "error": "public topic unavailable"})
                return
            if not isinstance(topics, list) or len(topics) != 1 or not isinstance(topics[0], dict):
                raise ValueError("expected one topic from V2EX")
            topic = topics[0]
            if str(topic.get("id")) != topic_id:
                raise ValueError("V2EX response did not match the requested topic")
            content = topic.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("V2EX topic has no text")
        except ValueError as exc:
            output.extraction_failures.append({"url": url, "error": str(exc)})
            return

        title = topic.get("title")
        excerpt = f"{title.strip()}\n\n{content.strip()}" if isinstance(title, str) and title.strip() else content.strip()
        output.sources.append(DraftSource(
            source_ref=f"v2ex:{topic_id}", origin="social_post", url=url, publisher="V2EX",
            locator=f"topic {topic_id}", excerpt=excerpt,
            observed_on=_publication_date(topic.get("created")), retrieved_on=date.today(),
        ))
