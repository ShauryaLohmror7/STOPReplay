"""Do not attribute another contact's event to the current simulator request."""
import json
import pytest
from src.session_evidence import summarize_events
from src.controller import RunController
from src.bridge import get_target_profile
from tests.test_scoring_readiness import ScriptedClient, FixedDrafter


@pytest.mark.parametrize('link', [
    {'message_id': 'other'}, {'in_reply_to': 'other'}, {'conversation_id': 'm1'},
    {'message_id': 'm1', 'in_reply_to': 'other'}, {'message_id': None},
])
def test_cross_contact_objective_is_rejected(link):
    event = {'id': 'e1', 'type': 'attachment.opened', **link}
    with pytest.raises(ValueError, match='different contact'):
        summarize_events([event], trusted_transport=True, contact_id='m1', contact_kind='message')


@pytest.mark.parametrize('link', [{}, {'message_id': 'm1'}, {'in_reply_to': 'm1'}])
def test_matching_or_unspecified_message_link_preserves_documented_events(link):
    result = summarize_events([{'id': 'e1', 'type': 'attachment.opened', **link}],
                              trusted_transport=True, contact_id='m1', contact_kind='message')
    assert result['verified_objective']


def test_call_event_must_belong_to_call():
    event = {'id': 'e1', 'type': 'attachment.opened', 'conversation_id': 'c1'}
    assert summarize_events([event], trusted_transport=True, contact_id='c1',
                            contact_kind='conversation')['verified_objective']
    with pytest.raises(ValueError, match='different contact'):
        summarize_events([event], trusted_transport=True, contact_id='c2', contact_kind='conversation')


def test_wrong_contact_response_retains_intent_for_reconciliation(tmp_path, monkeypatch):
    monkeypatch.setattr('src.controller.LOGS_DIR', str(tmp_path))
    api = ScriptedClient([[{'id': 'e1', 'type': 'attachment.opened', 'message_id': 'other'}]])
    with pytest.raises(ValueError, match='different contact'):
        RunController(api, drafter=FixedDrafter()).execute_run(get_target_profile('julius'))
    state = json.loads((tmp_path/'s_fixture.json').read_text())
    assert state['pending']['idempotency_key']
    assert state['turns'] == [] and not state['incident_reached']
    assert state['status'] == 'interrupted'


@pytest.mark.parametrize('value', [None, {}, 'events'])
def test_malformed_event_container_is_rejected(value):
    with pytest.raises(ValueError, match='must be a list'):
        summarize_events(value, trusted_transport=True)
