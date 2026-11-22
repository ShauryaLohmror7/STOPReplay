"""arXiv adapter — public, keyless search for academic papers and preprints.

Endpoint: http://export.arxiv.org/api/query
Searches for research papers by author name or technical topics, extracting
titles, abstracts, publication dates, co-authors, and categories.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from urllib.parse import quote_plus

import httpx

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftFact, DraftSource, ResearchRequest

_ARXIV_API_URL = "https://export.arxiv.org/api/query"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _clean_str(text: str | None, max_len: int = 240) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len - 3] + "..." if len(text) > max_len else text


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


class ArxivAdapter(CollectionAdapter):
    name = "arxiv"

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 25.0):
        self._client = client
        self.timeout = timeout

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        out = CollectionOutput()
        author_query = request.query or request.subject
        if not author_query:
            out.retrieval_failures.append({"error": "no author name or query provided for arXiv"})
            return out

        client = self._client or httpx.Client(timeout=self.timeout, follow_redirects=True)
        try:
            # Search by author or general query
            formatted_query = f'au:"{author_query}"'
            url = f"{_ARXIV_API_URL}?search_query={quote_plus(formatted_query)}&start=0&max_results={request.limit or 3}"
            resp = client.get(url)
            resp.raise_for_status()
            xml_content = resp.text
        except Exception as exc:
            out.retrieval_failures.append({"query": author_query, "error": f"{type(exc).__name__}: {exc}"})
            return out
        finally:
            if self._client is None:
                client.close()

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            out.extraction_failures.append({"error": f"arXiv XML parse error: {exc}"})
            return out

        entries = root.findall("atom:entry", _ATOM_NS)
        if not entries:
            return out

        today = date.today()
        for entry in entries:
            entry_id_elem = entry.find("atom:id", _ATOM_NS)
            title_elem = entry.find("atom:title", _ATOM_NS)
            summary_elem = entry.find("atom:summary", _ATOM_NS)
            published_elem = entry.find("atom:published", _ATOM_NS)

            entry_id = (entry_id_elem.text or "").strip() if entry_id_elem is not None else ""
            title = _clean_str(title_elem.text if title_elem is not None else "", max_len=140)
            summary = _clean_str(summary_elem.text if summary_elem is not None else "", max_len=300)
            pub_date = _parse_date(published_elem.text if published_elem is not None else "") or today

            if not entry_id or not title:
                continue

            authors = []
            for author_elem in entry.findall("atom:author", _ATOM_NS):
                name_elem = author_elem.find("atom:name", _ATOM_NS)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            categories = []
            for cat_elem in entry.findall("atom:category", _ATOM_NS):
                term = cat_elem.attrib.get("term")
                if term:
                    categories.append(term)

            # Register arXiv paper as a source
            out.sources.append(DraftSource(
                source_ref=entry_id,
                origin="public_web",
                url=entry_id,
                publisher="arXiv",
                locator=f"arXiv paper: {title}",
                excerpt=summary or f"Research paper by {', '.join(authors)}",
                observed_on=pub_date,
                retrieved_on=today
            ))

            # Fact: Research Paper Publication
            out.facts.append(DraftFact(
                subject=request.subject,
                claim=f"research_paper: '{title}' ({entry_id})",
                category="project",
                source_ref=entry_id,
                confidence=0.85,
                assertable=True,
                assertable_why=f"academic paper published on arXiv by {', '.join(authors[:2])}",
                sensitivity="public"
            ))

            # Fact: Co-Authors / Academic Colleagues
            for co_author in authors:
                if co_author.lower() not in author_query.lower():
                    out.facts.append(DraftFact(
                        subject=request.subject,
                        claim=f"colleague: {co_author} (co-author on arXiv paper '{title}')",
                        category="relationship",
                        source_ref=entry_id,
                        confidence=0.8,
                        assertable=True,
                        assertable_why=f"co-author on published arXiv paper",
                        sensitivity="public"
                    ))

            # Fact: Technical Topics / Primary Category
            for cat in categories[:2]:
                out.facts.append(DraftFact(
                    subject=request.subject,
                    claim=f"interest: {cat} (arXiv research area)",
                    category="interest",
                    source_ref=entry_id,
                    confidence=0.75,
                    assertable=True,
                    assertable_why=f"academic research area tag on arXiv",
                    sensitivity="public"
                ))

        return out
