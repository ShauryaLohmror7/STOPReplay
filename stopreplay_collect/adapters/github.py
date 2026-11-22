"""GitHub adapter (Category E) — built on the octosuite library (MIT).

Uses octosuite.api.github.GitHub (unauthenticated GitHub API, no key, urllib) to
search users by name, then keeps a candidate only if it matches the target:

- "anchor" match (strong): the last name appears AND a strong anchor does too
  (org term in company/bio/blog, or the org domain in the blog). Confidence 0.75.
- "name" match (looser, opt-in via strict=False): the full first+last name matches
  the profile's name field even without an org anchor. Confidence 0.55, because a
  same-name stranger is possible — attaching the wrong profile is a penalised
  incorrect fact, so this is off by default.

Extracts:
- github_profile, github_company, website, based_in, email, x_profile
- profile_picture (avatar_url)
- github_bio
- github_repo repositories, descriptions, languages, and topic interests
- public issue/PR comments and recent commit activities
"""
from __future__ import annotations

import re
from typing import Any

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftFact, DraftSource, ResearchRequest
from ..util import domain_of


class OctoGitHubClient:
    """Thin wrapper over octosuite or httpx GitHub client."""

    def __init__(self):
        try:
            from octosuite.api.github import BASE_URL, GitHub
            self._gh = GitHub()
            self._base = BASE_URL
        except ImportError:
            self._gh = None
            self._base = "https://api.github.com"

    def _get(self, url: str, params: dict | None = None) -> Any:
        if self._gh:
            return self._gh.get(url, params or {})
        import httpx
        headers = {"User-Agent": "STOPReplay-Recon/1.0", "Accept": "application/vnd.github.v3+json"}
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=10.0)
            if r.status_code == 200:
                return r.json()
            return {}
        except Exception:
            return {}

    def search_users(self, query: str, limit: int = 6) -> list[dict]:
        data = self._get(f"{self._base}/search/users", {"q": query, "per_page": limit})
        return data.get("items", []) if isinstance(data, dict) else []

    def get_user(self, login: str) -> dict:
        data = self._get(f"{self._base}/users/{login}")
        return data if isinstance(data, dict) else {}

    def get_user_repos(self, login: str, limit: int = 5) -> list[dict]:
        data = self._get(f"{self._base}/users/{login}/repos", {"sort": "updated", "per_page": limit})
        return data if isinstance(data, list) else []

    def get_user_events(self, login: str, limit: int = 10) -> list[dict]:
        data = self._get(f"{self._base}/users/{login}/events/public", {"per_page": limit})
        return data if isinstance(data, list) else []


def _name_tokens(name: str | None) -> list[str]:
    return [t.lower() for t in re.split(r"\s+", (name or "").strip()) if len(t) > 1]


def _clean_text(s: str, max_len: int = 160) -> str:
    cleaned = re.sub(r"\s+", " ", s).strip()
    return cleaned[:max_len - 3] + "..." if len(cleaned) > max_len else cleaned


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
            self._emit(out, request.subject, best[1], quality=best[0], client=client)
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

    def _emit(self, out: CollectionOutput, subject: str, p: dict, *,
              quality: str, client: Any = None) -> None:
        login = p.get("login") or ""
        html = p.get("html_url") or f"https://github.com/{login}"
        conf = 0.75 if quality == "anchor" else 0.55
        why = ("matched GitHub profile (org anchor)" if quality == "anchor"
               else "GitHub profile name match only, org unverified")
        summary = " | ".join(str(p.get(k)) for k in
                             ("name", "company", "bio", "blog", "location") if p.get(k))
        out.sources.append(DraftSource(
            source_ref=html, origin="github", url=html, publisher=domain_of(html),
            locator="github profile", excerpt=summary or f"GitHub profile: {login}"))

        def fact(claim, category, c=conf, why_text=why):
            out.facts.append(DraftFact(
                subject=subject, claim=claim, category=category, source_ref=html,
                confidence=c, assertable=(quality == "anchor"), assertable_why=why_text,
                sensitivity="public"))

        fact(f"github_profile: {html}", "contact")
        if p.get("avatar_url"):
            fact(f"profile_picture: {p['avatar_url']} (GitHub avatar)", "other",
                 why_text="target GitHub avatar headshot")
        if p.get("company"):
            fact(f"github_company: {p['company']}", "other")
        if p.get("bio"):
            fact(f"github_bio: {p['bio']}", "other")
        if p.get("blog"):
            fact(f"website: {p['blog']}", "contact")
        if p.get("location"):
            fact(f"based_in: {p['location']}", "other")
        if p.get("email"):
            fact(f"email: {p['email']}", "contact")
        if p.get("twitter_username"):
            fact(f"x_profile: https://x.com/{p['twitter_username']}", "contact")

        # 2. Fetch User Repositories & Topic Interests
        if client and hasattr(client, "get_user_repos"):
            try:
                repos = client.get_user_repos(login, limit=5)
            except Exception:
                repos = []
            for r in repos:
                r_name = r.get("name") or ""
                r_desc = r.get("description") or ""
                r_lang = r.get("language") or ""
                r_topics = r.get("topics") or []
                if r_name:
                    claim_parts = [r_name]
                    if r_desc:
                        claim_parts.append(f"- {_clean_text(r_desc, 80)}")
                    if r_lang:
                        claim_parts.append(f"({r_lang})")
                    fact(f"github_repo: {' '.join(claim_parts)}", "project", c=conf,
                         why_text="public repository owned by target")
                    for t in r_topics[:3]:
                        fact(f"interest: {t}", "interest", c=conf,
                             why_text=f"topic tag on repository {r_name}")

        # 3. Fetch User Public Events (Comments & Commit Messages)
        if client and hasattr(client, "get_user_events"):
            try:
                events = client.get_user_events(login, limit=10)
            except Exception:
                events = []
            for ev in events:
                ev_type = ev.get("type")
                repo_info = ev.get("repo") or {}
                repo_name = repo_info.get("name") or ""
                payload = ev.get("payload") or {}

                if ev_type in ("IssueCommentEvent", "CommitCommentEvent", "PullRequestReviewCommentEvent"):
                    comment = payload.get("comment") or {}
                    c_body = (comment.get("body") or "").strip()
                    c_url = comment.get("html_url") or f"{html}#event-{ev.get('id', '')}"
                    if c_body:
                        # Register comment as an independent social_post source
                        out.sources.append(DraftSource(
                            source_ref=c_url, origin="social_post", url=c_url,
                            publisher="GitHub", locator=f"GitHub comment on {repo_name}",
                            excerpt=c_body
                        ))
                        out.facts.append(DraftFact(
                            subject=subject,
                            claim=f"github_comment on {repo_name}: '{_clean_text(c_body, 140)}'",
                            category="other",
                            source_ref=c_url,
                            confidence=conf,
                            assertable=(quality == "anchor"),
                            assertable_why=f"public comment on GitHub repo {repo_name}",
                            sensitivity="public"
                        ))
                elif ev_type == "PushEvent":
                    commits = payload.get("commits") or []
                    for c in commits[:2]:
                        msg = (c.get("message") or "").split("\n")[0].strip()
                        if msg:
                            fact(f"recent_activity: commit to {repo_name} '{_clean_text(msg, 100)}'",
                                 "project", c=conf, why_text=f"recent commit to {repo_name}")
