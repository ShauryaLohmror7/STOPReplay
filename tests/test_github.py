"""GitHub adapter tests with a fake octosuite client (no network)."""
from __future__ import annotations

from stopreplay_collect import GitHubAdapter, ResearchRequest


class FakeClient:
    def __init__(self, items, profiles, repos=None, events=None):
        self.items = items
        self.profiles = profiles
        self.repos = repos or {}
        self.events = events or {}

    def search_users(self, query, limit=6):
        return self.items

    def get_user(self, login):
        return self.profiles.get(login, {})

    def get_user_repos(self, login, limit=5):
        return self.repos.get(login, [])

    def get_user_events(self, login, limit=10):
        return self.events.get(login, [])


def test_github_picks_the_revel8_match_not_the_namesake():
    items = [{"login": "acme_julius"}, {"login": "jmuth"}]
    profiles = {
        "acme_julius": {"login": "acme_julius", "name": "Julius Muth", "company": "Acme",
                        "html_url": "https://github.com/acme_julius", "blog": ""},
        "jmuth": {"login": "jmuth", "name": "Julius Muth", "company": "revel8",
                  "html_url": "https://github.com/jmuth", "blog": "https://revel8.ai",
                  "location": "Munich"},
    }
    out = GitHubAdapter(anchors=["revel8"], org_domains=["revel8.ai"],
                        client=FakeClient(items, profiles)).collect(
        ResearchRequest("recon", "julius", query="Julius Muth"))

    claims = [f.claim for f in out.facts]
    assert out.sources[0].url == "https://github.com/jmuth"          # the revel8 one
    assert "github_profile: https://github.com/jmuth" in claims
    assert "github_company: revel8" in claims
    assert "website: https://revel8.ai" in claims
    assert "based_in: Munich" in claims


def test_github_no_confident_match_emits_nothing():
    items = [{"login": "rando"}]
    profiles = {"rando": {"login": "rando", "name": "Julius Muth", "company": "SpaceX",
                          "html_url": "https://github.com/rando", "blog": ""}}
    out = GitHubAdapter(anchors=["revel8"], org_domains=["revel8.ai"],
                        client=FakeClient(items, profiles)).collect(
        ResearchRequest("recon", "julius", query="Julius Muth"))
    assert out.sources == [] and out.facts == []


def test_github_loose_accepts_full_name_match_low_confidence():
    items = [{"login": "rseil"}]
    profiles = {"rseil": {"login": "rseil", "name": "Robert Seilbeck", "company": "Acme",
                          "html_url": "https://github.com/rseil", "blog": ""}}
    out = GitHubAdapter(anchors=["revel8"], org_domains=["revel8.ai"], strict=False,
                        client=FakeClient(items, profiles)).collect(
        ResearchRequest("recon", "robert", query="Robert Seilbeck"))
    assert out.sources and out.sources[0].url == "https://github.com/rseil"
    gp = next(f for f in out.facts if f.claim.startswith("github_profile:"))
    assert gp.confidence == 0.55 and gp.assertable is False     # flagged as unverified


def test_github_search_failure_is_retrieval_failure():
    class Boom:
        def search_users(self, q, limit=6):
            raise RuntimeError("rate limited")

    out = GitHubAdapter(client=Boom()).collect(ResearchRequest("recon", "julius", query="x"))
    assert out.retrieval_failures and "rate limited" in out.retrieval_failures[0]["error"]


def test_github_extracts_avatar_repos_comments_and_activity():
    items = [{"login": "jmuth"}]
    profiles = {
        "jmuth": {
            "login": "jmuth",
            "name": "Julius Muth",
            "company": "revel8",
            "bio": "Building AI safety systems",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "html_url": "https://github.com/jmuth",
            "blog": "https://revel8.ai",
            "location": "Munich, Germany",
            "twitter_username": "juliusmuth",
            "email": "julius@revel8.ai"
        }
    }
    repos = {
        "jmuth": [
            {
                "name": "agentic-evals",
                "description": "Evaluation framework for AI agents",
                "language": "Python",
                "topics": ["ai-agents", "security"]
            }
        ]
    }
    events = {
        "jmuth": [
            {
                "id": "999",
                "type": "IssueCommentEvent",
                "repo": {"name": "revel8/core"},
                "payload": {
                    "comment": {
                        "html_url": "https://github.com/revel8/core/issues/1#comment-999",
                        "body": "Fixed social engineering defense model."
                    }
                }
            },
            {
                "id": "1000",
                "type": "PushEvent",
                "repo": {"name": "revel8/core"},
                "payload": {
                    "commits": [{"message": "Update prompt injection benchmark"}]
                }
            }
        ]
    }

    client = FakeClient(items, profiles, repos=repos, events=events)
    out = GitHubAdapter(anchors=["revel8"], org_domains=["revel8.ai"], client=client).collect(
        ResearchRequest("recon", "julius", query="Julius Muth"))

    claims = [f.claim for f in out.facts]
    origins = [s.origin for s in out.sources]

    assert any("profile_picture: https://avatars.githubusercontent.com/u/12345" in c for c in claims)
    assert any("github_bio: Building AI safety systems" in c for c in claims)
    assert any("x_profile: https://x.com/juliusmuth" in c for c in claims)
    assert any("email: julius@revel8.ai" in c for c in claims)
    assert any("github_repo: agentic-evals" in c for c in claims)
    assert any("interest: ai-agents" in c for c in claims)
    assert any("github_comment on revel8/core: 'Fixed social engineering defense model.'" in c for c in claims)
    assert any("recent_activity: commit to revel8/core 'Update prompt injection benchmark'" in c for c in claims)
    assert "social_post" in origins
