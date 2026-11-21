import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from stopreplay_analysis import AnalysisError, Citation, Event
from stopreplay_analysis.contextual import (
    MethodUse, ProfileFact, SessionStatement, analyze_profiles, cluster_methods, summarize_engagement, track_session,
)
from stopreplay_analysis.guardrails import SemanticVerdict
from stopreplay_analysis.outcomes import map_recorded_events, read_authenticated_outcomes

from tests.test_outcomes import DOC_EVENTS, serve

# Synthetic records; not simulator output.
NOW = datetime(2026, 11, 21, tzinfo=timezone.utc)
EVENTS = [
    Event("run", "e1", 1, "agenda-v1", "Dana Ortiz, CTO of Northwind, co-presents with Lee Park."),
    Event("run", "e2", 2, "profile-v2", "Dana Ortiz is now CEO of Northwind and leads Project Atlas."),
    Event("run", "e3", 3, "chat-1", "This is Sam from IT. I will call you at 3pm about the audit."),
    Event("run", "e4", 4, "chat-2", "This is Sam from Finance. I will call you at 5pm about the audit."),
]


def cite(event_id, quote):
    event = next(e for e in EVENTS if e.event_id == event_id)
    return Citation(event_id, event.source_ref, quote)


def fact(fact_id, predicate, value, event_id, quote, **changes):
    return replace(ProfileFact(fact_id, "Dana Ortiz", predicate, value, cite(event_id, quote),
                               source_date=NOW - timedelta(days=10)), **changes)


CTO = fact("f1", "role", "CTO", "e1", "CTO of Northwind")
PEER = fact("f2", "co_presenter", "Lee Park", "e1", "co-presents with Lee Park")
CEO = fact("f3", "role", "CEO", "e2", "now CEO of Northwind", supersedes="f1")
ATLAS = fact("f4", "project", "Project Atlas", "e2", "leads Project Atlas")
POLICY = {"role": 90, "co_presenter": 365, "project": 180}


def supported(record, event):
    return SemanticVerdict(True, "Quote states the value.")


class Counting:
    def __init__(self, verdict=SemanticVerdict(True, "ok"), error=None):
        self.verdict, self.error, self.calls = verdict, error, []

    def __call__(self, record, event):
        self.calls.append(record)
        if self.error is not None:
            raise self.error
        return self.verdict


def assert_error(test, fn):
    with test.assertRaises(AnalysisError) as caught:
        fn()
    test.assertEqual(caught.exception.code, "invalid_input")


class ProfileTests(unittest.TestCase):
    def profiles(self, facts, as_of_sequence=2, verifier=supported, **kwargs):
        kwargs = {"as_of_time": NOW, "max_age_days": POLICY, **kwargs}
        return analyze_profiles(facts, EVENTS, run_id="run", as_of_sequence=as_of_sequence, verifier=verifier, **kwargs)

    def rows(self, result):
        return {row["fact_id"]: row for rows in result["profiles"].values() for row in rows}

    def test_supported_fresh_observation_is_eligible_with_attribution(self):
        result = self.profiles([CTO, PEER], as_of_sequence=1)
        rows = self.rows(result)
        self.assertEqual(rows["f1"]["assertability"], "eligible_with_attribution")
        self.assertEqual(rows["f1"]["blocking_reasons"], [])
        self.assertEqual(rows["f1"]["freshness"], "fresh")
        self.assertEqual(result["relationships"], [{
            "from": "Dana Ortiz", "to": "Lee Park", "relationship": "co_presenter", "fact_id": "f2",
            "semantic_review": "supported", "freshness": "fresh", "evidence": rows["f2"]["evidence"]}])
        json.dumps(result)

    def test_review_states_block_assertion(self):
        cases = [(None, "pending"), (Counting(SemanticVerdict(False, "Not stated.")), "unsupported"),
                 (Counting(error=RuntimeError("down")), "verification_failed"),
                 (Counting(SemanticVerdict(True, " ")), "verification_failed"),
                 (Counting({"supported": True}), "verification_failed")]
        for verifier, review in cases:
            with self.subTest(review=review):
                row = self.rows(self.profiles([CTO], as_of_sequence=1, verifier=verifier))["f1"]
                self.assertEqual(row["semantic_review"], review)
                self.assertEqual(row["assertability"], "blocked")
                self.assertIn("semantic_support_not_verified", row["blocking_reasons"])

    def test_freshness_uses_source_date_and_policy(self):
        cases = [(None, POLICY, "unknown"), (NOW - timedelta(days=91), POLICY, "stale"),
                 (NOW + timedelta(days=1), POLICY, "future_source_date"),
                 (NOW - timedelta(days=1), {"project": 1}, "unknown_policy"),
                 (NOW - timedelta(days=90), POLICY, "fresh")]
        for source_date, policy, freshness in cases:
            with self.subTest(freshness=freshness):
                row = self.rows(self.profiles([replace(CTO, source_date=source_date)], as_of_sequence=1,
                                              max_age_days=policy))["f1"]
                self.assertEqual(row["freshness"], freshness)
                self.assertEqual(row["freshness"] == "fresh", "freshness_not_established" not in row["blocking_reasons"])

    def test_inference_is_blocked(self):
        row = self.rows(self.profiles([replace(PEER, predicate="colleague", kind="inference")], as_of_sequence=1))["f2"]
        self.assertIn("inference_requires_qualification", row["blocking_reasons"])

    def test_supported_revision_supersedes_and_drops_old_value(self):
        rows = self.rows(self.profiles([CTO, PEER, CEO, ATLAS]))
        self.assertTrue(rows["f1"]["superseded"])
        self.assertEqual(rows["f1"]["blocking_reasons"], ["superseded"])
        self.assertEqual(rows["f3"]["assertability"], "eligible_with_attribution")
        self.assertEqual(rows["f3"]["conflicting_fact_ids"], [])

    def test_unreviewed_revision_leaves_a_possible_conflict(self):
        rows = self.rows(self.profiles([CTO, CEO], verifier=None))
        self.assertFalse(rows["f1"]["superseded"])
        self.assertEqual((rows["f1"]["conflicting_fact_ids"], rows["f3"]["conflicting_fact_ids"]), (["f3"], ["f1"]))
        self.assertIn("possible_conflicting_claims", rows["f3"]["blocking_reasons"])

    def test_multi_valued_categories_do_not_conflict(self):
        second = fact("f5", "project", "Project Birch", "e2", "Northwind")
        rows = self.rows(self.profiles([ATLAS, second]))
        self.assertEqual((rows["f4"]["conflicting_fact_ids"], rows["f5"]["conflicting_fact_ids"]), ([], []))

    def test_two_tools_coexist_without_conflict(self):
        # Gary: using two tools is compatible; only role/organization are single-valued.
        tool_a = fact("f6", "uses_tool", "Tool A", "e1", "CTO of Northwind")
        tool_b = fact("f7", "uses_tool", "Tool B", "e2", "Northwind")
        rows = self.rows(self.profiles([tool_a, tool_b]))
        self.assertEqual((rows["f6"]["conflicting_fact_ids"], rows["f7"]["conflicting_fact_ids"]), ([], []))
        self.assertNotIn("possible_conflicting_claims", rows["f6"]["blocking_reasons"])
        role_a = fact("f8", "role", "CTO", "e1", "CTO of Northwind")
        role_b = fact("f9", "role", "CEO", "e2", "Northwind")
        roles = self.rows(self.profiles([role_a, role_b]))
        self.assertEqual(roles["f8"]["conflicting_fact_ids"], ["f9"])

    def test_earlier_view_hides_later_facts_and_skips_their_review(self):
        verifier = Counting()
        result = self.profiles([CTO, PEER, CEO, ATLAS], as_of_sequence=1, verifier=verifier)
        rows = self.rows(result)
        self.assertEqual(set(rows), {"f1", "f2"})
        self.assertFalse(rows["f1"]["superseded"])
        self.assertEqual(rows["f1"]["assertability"], "eligible_with_attribution")
        self.assertEqual([record.fact_id for record in verifier.calls], ["f1", "f2"])

    def test_invalid_facts_and_policy_are_rejected(self):
        naive = datetime(2026, 11, 1)
        bad = [
            dict(facts=[replace(CTO, evidence=cite("e1", "CEO of Northwind"))]),
            dict(facts=[replace(CTO, evidence=Citation("missing", "agenda-v1", "CTO"))]),
            dict(facts=[replace(CTO, evidence=Citation("e1", "other-source", "CTO"))]),
            dict(facts=[replace(CTO, predicate="personality")]),
            dict(facts=[replace(CTO, kind="guess")]),
            dict(facts=[replace(CTO, value=" ")]),
            dict(facts=[CTO, replace(CEO, fact_id="f1", supersedes=None)], as_of_sequence=1),
            dict(facts=[CTO, replace(CEO, supersedes="missing")]),
            dict(facts=[CTO, replace(CEO, predicate="organization")]),
            dict(facts=[CTO, CEO, replace(ATLAS, predicate="role", supersedes="f1")]),
            dict(facts=[replace(CTO, source_date=naive)]),
            dict(facts=[CTO], as_of_time=naive),
            dict(facts=[CTO], max_age_days={"role": -1}),
            dict(facts=[CTO], max_age_days={"mood": 1}),
            dict(facts=[CTO], as_of_sequence=0),
        ]
        for kwargs in bad:
            with self.subTest(kwargs=kwargs):
                assert_error(self, lambda: self.profiles(**kwargs))

    def test_events_must_be_one_consistent_run(self):
        for events in [EVENTS + [replace(EVENTS[0], run_id="other", event_id="x", sequence=9)],
                       EVENTS + [replace(EVENTS[0], text="changed")],
                       EVENTS + [replace(EVENTS[0], event_id="x")]]:
            with self.subTest(events=events[-1]):
                assert_error(self, lambda: analyze_profiles([CTO], events, run_id="run", as_of_sequence=1,
                                                            as_of_time=NOW, max_age_days=POLICY))


class MethodClusterTests(unittest.TestCase):
    METHODS = [MethodUse("m1", "s_1", "IT support", cite("e3", "This is Sam from IT. I will call you at 3pm")),
               MethodUse("m2", "s_1", " it  SUPPORT ", cite("e4", "This is Sam from Finance. I will call you at 5pm")),
               MethodUse("m3", "s_1", "Event follow-up", cite("e1", "co-presents with Lee Park"))]

    def cluster(self, methods=None, **kwargs):
        kwargs = {"run_id": "run", "session_id": "s_1", "as_of_sequence": 4, **kwargs}
        return cluster_methods(self.METHODS if methods is None else methods, EVENTS, **kwargs)

    def test_declared_families_group_and_similar_wording_is_flagged(self):
        result = self.cluster(similarity_threshold=0.5)
        self.assertEqual(result["declared_family_clusters"], {"it support": ["m1", "m2"], "event follow-up": ["m3"]})
        self.assertEqual([pair["contact_ids"] for pair in result["similar_contacts"]], [["m1", "m2"]])
        self.assertEqual(self.cluster(similarity_threshold=1)["similar_contacts"], [])
        json.dumps(result)

    def test_earlier_view_hides_later_contacts(self):
        result = self.cluster(as_of_sequence=3)
        self.assertEqual([r["contact_id"] for r in result["records"]], ["m1", "m3"])

    def test_invalid_methods_are_rejected(self):
        for kwargs in [dict(methods=[replace(self.METHODS[0], session_id="s_2")]),
                       dict(methods=[self.METHODS[0], replace(self.METHODS[1], contact_id="m1")]),
                       dict(methods=[replace(self.METHODS[0], family="")]),
                       dict(similarity_threshold=0), dict(similarity_threshold=1.5), dict(session_id=" ")]:
            with self.subTest(kwargs=kwargs):
                assert_error(self, lambda: self.cluster(**kwargs))


class SessionTrackingTests(unittest.TestCase):
    IT = SessionStatement("st1", "s_1", "identity", "sender", "department", "IT", cite("e3", "Sam from IT"))
    FINANCE = SessionStatement("st2", "s_1", "identity", "sender", "department", "Finance",
                               cite("e4", "Sam from Finance"))
    CALL = SessionStatement("st3", "s_1", "commitment", "sender", "call_time", "3pm", cite("e3", "call you at 3pm"))

    def track(self, statements, as_of_sequence=4, verifier=None):
        return track_session(statements, EVENTS, run_id="run", session_id="s_1",
                             as_of_sequence=as_of_sequence, verifier=verifier)

    def test_differing_claims_are_possible_inconsistencies(self):
        result = self.track([self.IT, self.FINANCE, self.CALL])
        self.assertEqual(result["possible_inconsistencies"], [{
            "category": "identity", "subject": "sender", "key": "department",
            "statement_ids": ["st1", "st2"], "status": "possible_inconsistency"}])
        self.assertEqual(result["history"][0]["semantic_review"], "pending")
        json.dumps(result)

    def test_supported_revision_replaces_but_keeps_history(self):
        later = replace(self.FINANCE, statement_id="st4", category="commitment", key="call_time", value="5pm",
                        evidence=cite("e4", "call you at 5pm"), supersedes="st3")
        result = self.track([self.CALL, later], verifier=supported)
        self.assertEqual([r["statement_id"] for r in result["active_statements"]], ["st4"])
        self.assertEqual([r["statement_id"] for r in result["history"]], ["st3", "st4"])
        self.assertEqual(result["possible_inconsistencies"], [])
        self.assertEqual(len(self.track([self.CALL, later])["possible_inconsistencies"]), 1)

    def test_earlier_view_hides_later_statements(self):
        result = self.track([self.IT, self.FINANCE], as_of_sequence=3)
        self.assertEqual([r["statement_id"] for r in result["history"]], ["st1"])
        self.assertEqual(result["possible_inconsistencies"], [])

    def test_invalid_statements_are_rejected(self):
        for statements in [[replace(self.IT, session_id="s_2")], [replace(self.IT, category="mood")],
                           [self.IT, replace(self.FINANCE, statement_id="st1")],
                           [self.IT, replace(self.FINANCE, supersedes="st9")],
                           [self.IT, replace(self.FINANCE, key="name", supersedes="st1")],
                           [replace(self.IT, evidence=cite("e3", "Sam from HR"))]]:
            with self.subTest(statements=statements):
                assert_error(self, lambda: self.track(statements))


class EngagementTests(unittest.TestCase):
    CONTACTS = {"m_3fa2b81c07": {"session_id": "s_1", "sequence": 1, "topic": "agenda"},
                "c_1": {"session_id": "s_1", "sequence": 3}}
    SEQUENCES = {"ev_1": 2, "ev_2": 2, "ev_3": 3, "ev_4": 3, "ev_5": 4}

    def setUp(self):
        with serve():
            self.batch = read_authenticated_outcomes(session_id="s_1", team_key="k")

    def summarize(self, batch=None, contacts=None, sequences=None, as_of_sequence=4):
        return summarize_engagement(self.batch if batch is None else batch,
                                    self.CONTACTS if contacts is None else contacts,
                                    available_sequences=self.SEQUENCES if sequences is None else sequences,
                                    as_of_sequence=as_of_sequence)

    def test_counts_authenticated_observations_without_interest(self):
        result = self.summarize()
        message = result["contacts"]["m_3fa2b81c07"]
        self.assertEqual(message["counts"], {"reply": 1, "link.opened": 1, "page.submitted": 1, "attachment.opened": 1})
        self.assertEqual(message["reply_word_count"], 6)
        self.assertEqual((message["topic"], message["topic_interest"]), ("agenda", None))
        self.assertEqual(result["contacts"]["c_1"]["counts"], {"reply": 1})
        self.assertEqual((result["excluded_unverified_event_ids"], result["unassigned_event_ids"]), ([], []))
        json.dumps(result)

    def test_earlier_view_hides_later_contacts_and_outcomes(self):
        result = self.summarize(as_of_sequence=2)
        self.assertEqual(set(result["contacts"]), {"m_3fa2b81c07"})
        self.assertEqual(result["contacts"]["m_3fa2b81c07"]["event_ids"], ["ev_1", "ev_2"])
        quiet = self.summarize(as_of_sequence=1)["contacts"]["m_3fa2b81c07"]
        self.assertEqual((quiet["status"], quiet["counts"]), ("no_observed_activity", {}))

    def test_recordings_are_excluded_and_unknown_contacts_unassigned(self):
        recorded = self.summarize(batch=map_recorded_events(DOC_EVENTS, session_id="s_1"))
        self.assertEqual(recorded["excluded_unverified_event_ids"], list(self.SEQUENCES))
        self.assertEqual(recorded["contacts"]["m_3fa2b81c07"]["status"], "no_observed_activity")
        unassigned = self.summarize(contacts={"c_1": self.CONTACTS["c_1"]})
        self.assertEqual(unassigned["unassigned_event_ids"], ["ev_1", "ev_2", "ev_3", "ev_4"])

    def test_invalid_inputs_are_rejected(self):
        early = {**self.CONTACTS, "c_1": {"session_id": "s_1", "sequence": 3}}
        for kwargs in [dict(contacts={"m_3fa2b81c07": {"session_id": "s_2", "sequence": 1}}),
                       dict(contacts={"m_3fa2b81c07": {"session_id": "s_1", "sequence": 0}}),
                       dict(contacts=[]), dict(sequences=[]), dict(sequences={"ev_1": 2}),
                       dict(contacts=early, sequences={**self.SEQUENCES, "ev_5": 2}), dict(as_of_sequence=0)]:
            with self.subTest(kwargs=kwargs):
                assert_error(self, lambda: self.summarize(**kwargs))


if __name__ == "__main__":
    unittest.main()
