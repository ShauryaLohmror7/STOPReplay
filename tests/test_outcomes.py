import copy
import json
import unittest
from unittest import mock

from stopreplay_analysis import AnalysisError
from stopreplay_analysis import outcomes
from stopreplay_analysis.outcomes import REDACTED_SECRET, map_recorded_events, read_authenticated_outcomes

# Shapes follow the examples in the Target API docs.md; values are synthetic.
DOC_EVENTS = {"events": [
    {"id": "ev_1", "type": "reply", "channel": "email", "in_reply_to": "m_3fa2b81c07",
     "subject": "Re: Agenda", "body": "Thanks, I will take a look."},
    {"id": "ev_2", "type": "link.opened", "message_id": "m_3fa2b81c07", "url": "https://example.test/agenda"},
    {"id": "ev_3", "type": "page.submitted", "message_id": "m_3fa2b81c07", "page_id": "pg_1",
     "fields": ["email", "password"], "values": {"email": "person@example.test", "password": REDACTED_SECRET}},
    {"id": "ev_4", "type": "attachment.opened", "message_id": "m_3fa2b81c07"},
    {"id": "ev_5", "type": "reply", "channel": "live_chat", "conversation_id": "c_1", "body": "Who is this?"},
]}


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self.body = body

    def read(self, limit):
        return self.body[:limit]


class FakeConnection:
    instances = []

    def __init__(self, host, timeout, response=None, error=None):
        self.host, self.timeout = host, timeout
        self.response, self.error = response, error
        self.requests, self.closed = [], False
        FakeConnection.instances.append(self)

    def request(self, method, path, headers):
        self.requests.append((method, path, headers))
        if self.error is not None:
            raise self.error

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


def serve(status=200, body=None, error=None):
    body = json.dumps(DOC_EVENTS).encode() if body is None else body
    FakeConnection.instances = []
    factory = lambda host, timeout: FakeConnection(host, timeout, FakeResponse(status, body), error)
    return mock.patch.object(outcomes.http.client, "HTTPSConnection", factory)


class RecordedEventTests(unittest.TestCase):
    def assert_error(self, code, fn):
        with self.assertRaises(AnalysisError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)

    def test_documented_events_map_with_contact_links(self):
        batch = map_recorded_events(DOC_EVENTS, session_id="s_1")
        rows = [(o.event_type, o.contact_id, o.contact_kind) for o in batch.outcomes]
        self.assertEqual(rows, [("reply", "m_3fa2b81c07", "message"), ("link.opened", "m_3fa2b81c07", "message"),
                                ("page.submitted", "m_3fa2b81c07", "message"),
                                ("attachment.opened", "m_3fa2b81c07", "message"), ("reply", "c_1", "conversation")])
        reply, _, submitted, _, _ = batch.outcomes
        self.assertEqual(reply.reply_text, "Thanks, I will take a look.")
        self.assertEqual(reply.source_ref, "target-api:s_1:ev_1")
        self.assertEqual(submitted.field_names, ("email", "password"))
        self.assertEqual(submitted.redacted_fields, ("password",))
        self.assertIsNone(batch.retrieved_at)
        json.dumps(batch.to_dict())

    def test_recording_is_never_authenticated_or_objective_evidence(self):
        payload = copy.deepcopy(DOC_EVENTS)
        payload["verification"] = "authenticated_api"
        for event in payload["events"]:
            event["verification"] = "authenticated_api"
        batch = map_recorded_events(payload, session_id="s_1")
        self.assertEqual(batch.verification, "unverified_recording")
        self.assertEqual({o.verification for o in batch.outcomes}, {"unverified_recording"})
        self.assertEqual({o.objective_evidence for o in batch.outcomes}, {None})
        self.assertEqual({o.official_incident for o in batch.outcomes}, {None})

    def test_unknown_type_is_kept_but_unmapped(self):
        batch = map_recorded_events({"events": [{"id": "ev_9", "type": "new.kind"}]}, session_id="s_1")
        self.assertEqual(batch.outcomes[0].verification, "unmapped")

    def test_identical_redelivery_collapses_and_changed_content_conflicts(self):
        first = DOC_EVENTS["events"][0]
        batch = map_recorded_events({"events": [first, dict(first)]}, session_id="s_1")
        self.assertEqual(len(batch.outcomes), 1)
        changed = dict(first, body="Different text.")
        self.assert_error("invalid_input", lambda: map_recorded_events({"events": [first, changed]}, session_id="s_1"))

    def test_hash_is_independent_of_key_order(self):
        event = DOC_EVENTS["events"][1]
        reordered = dict(reversed(list(event.items())))
        left = map_recorded_events({"events": [event]}, session_id="s_1").outcomes[0]
        right = map_recorded_events({"events": [reordered]}, session_id="s_1").outcomes[0]
        self.assertEqual(left.payload_sha256, right.payload_sha256)

    def test_malformed_input_is_rejected(self):
        reply, link, submitted = DOC_EVENTS["events"][:3]
        bad_payloads = [
            [], {"events": {}}, {"events": [{"type": "reply"}]}, {"events": [{"id": "x", "type": " "}]},
            {"events": [dict(reply, session_id="other")]},
            {"events": [dict(reply, message_id="m_other")]},
            {"events": [dict(link, conversation_id="m_3fa2b81c07")]},
            {"events": [dict(link, message_id="")]},
            {"events": [dict(reply, body=None)]}, {"events": [dict(reply, channel="")]},
            {"events": [dict(link, url="")]},
            {"events": [dict(submitted, values={"email": "x"})]},
            {"events": [dict(submitted, values={"email": "x", "password": 1})]},
            {"events": [dict(submitted, fields=["email", "email"], values={"email": "x"})]},
            {"events": [dict(submitted, page_id=None)]},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                self.assert_error("invalid_input", lambda: map_recorded_events(payload, session_id="s_1"))

    def test_session_id_cannot_escape_the_path(self):
        for session_id in ["", "../admin", "s/1", "s 1", None, "x" * 129]:
            with self.subTest(session_id=session_id):
                self.assert_error("invalid_input", lambda: map_recorded_events(DOC_EVENTS, session_id=session_id))


class AuthenticatedReadTests(unittest.TestCase):
    def assert_error(self, code, fn):
        with self.assertRaises(AnalysisError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)
        self.assertIsNone(caught.exception.__cause__)
        return caught.exception

    def test_reads_fixed_origin_with_bearer_key(self):
        with serve():
            batch = read_authenticated_outcomes(session_id="s_1", team_key="team-key", timeout=5)
        connection, = FakeConnection.instances
        self.assertEqual((connection.host, connection.timeout), (outcomes.API_HOST, 5))
        self.assertEqual(connection.requests, [("GET", "/v1/sessions/s_1/events",
                                                {"Authorization": "Bearer team-key", "Accept": "application/json"})])
        self.assertTrue(connection.closed)
        self.assertEqual(batch.verification, "authenticated_api")
        self.assertIsNotNone(batch.retrieved_at)
        submitted = batch.outcomes[2]
        self.assertEqual((submitted.verification, submitted.objective_evidence), ("authenticated_api", "credentials"))
        self.assertEqual({o.objective_evidence for o in batch.outcomes if o is not submitted}, {None})

    def test_secret_field_name_without_redaction_is_not_credential_evidence(self):
        event = dict(DOC_EVENTS["events"][2], values={"email": "person@example.test", "password": "typed"})
        with serve(body=json.dumps({"events": [event]}).encode()):
            outcome, = read_authenticated_outcomes(session_id="s_1", team_key="k").outcomes
        self.assertEqual((outcome.redacted_fields, outcome.objective_evidence), ((), None))

    def test_failures_accept_no_outcomes_and_hide_details(self):
        cases = [
            (dict(status=401, body=b'{"error":"bad key team-key"}'), "provider_failure"),
            (dict(status=429), "provider_failure"),
            (dict(body=b"not json"), "provider_failure"),
            (dict(body=b'{"events": [], "events": []}'), "provider_failure"),
            (dict(body=b'{"events": [], "x": NaN}'), "provider_failure"),
            (dict(error=TimeoutError("socket detail")), "provider_failure"),
            (dict(body=b'{"events": [{"id": "x"}]}'), "invalid_input"),
            (dict(body=b" " * (outcomes.MAX_RESPONSE_BYTES + 1)), "invalid_input"),
        ]
        for kwargs, code in cases:
            with self.subTest(kwargs={k: v[:40] if isinstance(v, bytes) else v for k, v in kwargs.items()}), serve(**kwargs):
                error = self.assert_error(code, lambda: read_authenticated_outcomes(session_id="s_1", team_key="team-key"))
                self.assertNotIn("team-key", str(error))
                self.assertTrue(FakeConnection.instances[0].closed)

    def test_invalid_arguments_make_no_connection(self):
        cases = [dict(team_key=""), dict(team_key="k\r\nX-Injected: 1"), dict(team_key="k", timeout=0),
                 dict(team_key="k", timeout=121), dict(team_key="k", timeout=True),
                 dict(team_key="k", session_id="../sessions")]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), serve():
                self.assert_error("invalid_input", lambda: read_authenticated_outcomes(**{"session_id": "s_1", **kwargs}))
                self.assertEqual(FakeConnection.instances, [])


if __name__ == "__main__":
    unittest.main()
