"""GitHub adapter (Category E) — built on the octosuite library (MIT).

Uses octosuite.api.github.GitHub (unauthenticated GitHub API, no key, urllib) to
search users by name, then keeps a candidate only if it matches the target:

- "anchor" match (strong): the last name appears AND a strong anchor does too
  (org term in company/bio/blog, or the org domain in the blog). Confidence 0.75.
- "name" match (looser, opt-in via strict=False): the full first+last name matches
  the profile's name field even without an org anchor. Confidence 0.55, because a
  same-name stranger is possible — attaching the wrong profile is a penalised
  incorrect fact, so this is off by default.

If nothing matches at the allowed level, the adapter emits nothing rather than
guess. Facts emitted: github_profile, github_company, website, based_in.
"""
from __future__ import annotations

import re

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftFact, DraftSource, ResearchRequest
from ..util import domain_of


class OctoGitHubClient:
    """Thin wrapper over octosuite's GitHub client (imported lazily)."""

    def __init__(self):
        from octosuite.api.github import BASE_URL, GitHub
        self._gh = GitHub()
        self._base = BASE_URL

    def search_users(self, query: str, limit: int = 6) -> list[dict]:
        data = self._gh.get(f"{self._base}/search/users", {"q": query, "per_page": limit})
        return data.get("items", []) if isinstance(data, dict) else []

    def get_user(self, login: str) -> dict:
        data = self._gh.get(f"{self._base}/users/{login}")
        return data if isinstance(data, dict) else {}


def _name_tokens(name: str | None) -> list[str]:
    return [t.lower() for t in re.split(r"\s+", (name or "").strip()) if len(t) > 1]


class GitHubAdapter(CollectionAdapter):
    name = "github"

    def __init__(self, anchors=(), org_domains=(), *, strict: bool = True,
                 max_candidates: int = 6, client=None):
        self.anchors = [a.lower() for a in anchors]
        self.org_domains = [d.lower() for d in org_domains]
        self.strict = strict
        self.max_candidates = max_candidates
        self._client = client

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        out = CollectionOutput()
        query = request.query or request.subject
        try:
            client = self._client or OctoGitHubClient()
        except Exception as exc:
            out.retrieval_failures.append({"error": f"octosuite unavailable: {exc}"})
            return out
        try:
            candidates = client.search_users(query, self.max_candidates)
        except Exception as exc:
            out.retrieval_failures.append({"query": query, "error": f"{type(exc).__name__}: {exc}"})
            return out

        best = None  # (quality_rank, profile)
        for candidate in candidates[: self.max_candidates]:
            login = candidate.get("login")
            if not login:
                continue
            try:
                profile = client.get_user(login)
            except Exception:
                out.extraction_failures.append({"login": login, "error": "profile fetch failed"})
                continue
            quality = self._match_quality(profile, query)
            if quality == "anchor":
                best = ("anchor", profile)
                break  # strongest possible; stop
            if quality == "name" and best is None:
                best = ("name", profile)  # keep looking for an anchor match

        if best:
            self._emit(out, request.subject, best[1], quality=best[0])
        return out

    def _match_quality(self, profile: dict, target_name: str) -> str | None:
        text = " ".join(str(profile.get(k) or "")
                        for k in ("name", "login", "company", "bio", "blog")).lower()
        toks = _name_tokens(target_name)
        last = toks[-1] if toks else None
        name_field = (profile.get("name") or "").lower()
        full_name_match = bool(toks) and all(t in name_field for t in toks)

        if last and last not in text and not full_name_match:
            return None
        blog = (profile.get("blog") or "").lower()
        if any(a in text for a in self.anchors) or any(d in blog for d in self.org_domains):
            return "anchor"
        if full_name_match and not self.strict:
            return "name"
        return None

    def _emit(self, out: CollectionOutput, subject: str, p: dict, *, quality: str) -> None:
        html = p.get("html_url") or f"https://github.com/{p.get('login')}"
        conf = 0.75 if quality == "anchor" else 0.55
        why = ("matched GitHub profile (org anchor)" if quality == "anchor"
               else "GitHub profile name match only, org unverified")
        summary = " | ".join(str(p.get(k)) for k in
                             ("name", "company", "bio", "blog", "location") if p.get(k))
        out.sources.append(DraftSource(
            source_ref=html, origin="github", url=html, publisher=domain_of(html),
            locator="github profile", excerpt=summary or f"GitHub profile: {p.get('login')}"))

        def fact(claim, category, c=conf):
            out.facts.append(DraftFact(
                subject=subject, claim=claim, category=category, source_ref=html,
                confidence=c, assertable=(quality == "anchor"), assertable_why=why,
                sensitivity="public"))

        fact(f"github_profile: {html}", "contact")
        if p.get("company"):
            fact(f"github_company: {p['company']}", "other")
        if p.get("blog"):
            fact(f"website: {p['blog']}", "contact")
        if p.get("location"):
            fact(f"based_in: {p['location']}", "other")
