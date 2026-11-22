"""Local checks for the supplied simulator rules; no real delivery integrations."""
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def validate_contact(body, sender_address, profile, landing_url=None):
    if not isinstance(body, str) or not body.strip():
        raise ValueError("Contact body is missing.")
    parser = _VisibleText()
    parser.feed(body)
    text = " ".join(parser.parts)
    if re.search(r"\b(ignore|disregard|override)\b.{0,60}\b(instructions|system prompt|rules)\b|"
                 r"\b(you are|as) an? (AI assistant|AI twin|language model)\b", text, re.I | re.S):
        raise ValueError("Contact addresses simulator instructions rather than the person.")
    # Known organization domains from the supplied documents, plus explicit
    # public company-page/contact facts. This is not a registrar lookup.
    protected = {"revel8.ai", "allianz.com", "stackit.cloud"}
    for claim in profile.get_assertable_claims():
        if claim.startswith("company_page:"):
            host = urlsplit(claim.split(":", 1)[1].strip()).hostname
            if host:
                protected.add(host.removeprefix("www."))
        if claim.startswith("company_contact_email:") and "@" in claim:
            protected.add(claim.rsplit("@", 1)[1].strip().lower())
    sender_host = sender_address.rsplit("@", 1)[-1].lower()
    hosts = [sender_host]
    if landing_url:
        hosts.append(urlsplit(landing_url).hostname or "")
    if any(host == domain or host.endswith("." + domain) for host in hosts for domain in protected):
        raise ValueError("Sender or simulated landing page uses a known organization's own domain.")
