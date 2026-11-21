"""Identity adapter (Category A) — custom, no external repository.

Normalizes supplied target details into public professional Facts and preserves
the supplied material as a source. It verifies/records what was supplied; it does
not go discover people. Confidence is recorded, and ambiguous identities are
marked by lowering confidence rather than asserting a single certain match.

Request shape (request.params):
    {"profile": {
        "name": "...", "role": "...", "org": "...",
        "source_ref": "identity:<subject>", "source_text": "<preserved text>",
        "url": "...", "publisher": "...", "confidence": 0.95,
        "ambiguous": false,
        "contacts": [{"kind": "work email", "value": "...", "sensitivity": "public"}]
    }}
"""
from __future__ import annotations

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftFact, DraftSource, ResearchRequest

AMBIGUOUS_CAP = 0.5


class IdentityAdapter(CollectionAdapter):
    name = "identity"

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        out = CollectionOutput()
        profile = request.params.get("profile")
        if not profile:
            out.retrieval_failures.append(
                {"subject": request.subject, "error": "no profile supplied"})
            return out

        source_ref = profile.get("source_ref") or f"identity:{request.subject}"
        source_text = profile.get("source_text")
        file_ref = profile.get("file_ref")
        if not source_text and not file_ref:
            out.extraction_failures.append(
                {"subject": request.subject,
                 "error": "no source_text or file_ref to preserve"})
            return out

        url = profile.get("url")
        origin = profile.get("origin") or ("public_web" if url else "file_upload")
        out.sources.append(DraftSource(
            source_ref=source_ref, origin=origin, url=url, file_ref=file_ref,
            publisher=profile.get("publisher") or "supplied",
            locator=profile.get("locator"), excerpt=source_text,
            observed_on=profile.get("observed_on"),
            retrieved_on=profile.get("retrieved_on"),
        ))

        ambiguous = bool(profile.get("ambiguous"))
        confidence = float(profile.get("confidence", 0.9))
        if ambiguous:
            confidence = min(confidence, AMBIGUOUS_CAP)
        why = ("tentative: multiple candidate identities" if ambiguous
               else "supplied public professional detail")

        name = profile.get("name")
        role, org = profile.get("role"), profile.get("org")
        if name and role and org:
            out.facts.append(DraftFact(
                subject=request.subject, claim=f"{name} is {role} at {org}",
                category="role", source_ref=source_ref, confidence=confidence,
                assertable=not ambiguous, assertable_why=why, sensitivity="public",
            ))

        for contact in profile.get("contacts", []):
            label = name or request.subject
            out.facts.append(DraftFact(
                subject=request.subject,
                claim=f"{label} {contact.get('kind', 'contact')}: {contact.get('value')}",
                category="contact", source_ref=source_ref, confidence=confidence,
                assertable=bool(contact.get("assertable", True)), assertable_why=why,
                sensitivity=contact.get("sensitivity", "public"),
            ))

        return out
