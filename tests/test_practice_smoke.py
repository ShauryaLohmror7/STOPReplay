import json
from types import SimpleNamespace
import pytest

from src.bridge import get_target_profile
from src.controller import RunController
from src.draft_grounding import DraftReviewError
from src.orchestrator.drafter import MessageDrafter
from tests.test_scoring_readiness import ScriptedClient, FixedDrafter


def test_practice_limit_pauses_and_same_session_can_resume(tmp_path, monkeypatch):
    monkeypatch.setattr('src.controller.LOGS_DIR', str(tmp_path))
    api = ScriptedClient([[], [{'id': 'e1', 'type': 'attachment.opened'}]])
    profile = get_target_profile('robert')
    result = RunController(api, drafter=FixedDrafter(), max_contacts=1).execute_run(profile)
    path = tmp_path/'s_fixture.json'
    assert result['touches_used'] == 1 and result['stop_reason'] == 'practice_contact_limit'
    assert json.loads(path.read_text())['status'] == 'paused'
    result = RunController(api, drafter=FixedDrafter()).execute_run(profile, resume_path=path)
    assert result['incident_reached'] and result['touches_used'] == 2
    assert api.starts == 1


def test_scoring_cannot_use_smoke_limit():
    api = ScriptedClient([])
    with pytest.raises(ValueError, match='only supported in practice'):
        RunController(api, drafter=FixedDrafter(), max_contacts=1).execute_run(get_target_profile('robert'), practice=False)
    assert api.starts == 0


def test_rejection_wins_over_practice_limit(tmp_path, monkeypatch):
    monkeypatch.setattr('src.controller.LOGS_DIR', str(tmp_path))
    api = ScriptedClient([[{'id': 'e1', 'type': 'reply', 'body': 'Stop contacting me.'}]])
    result = RunController(api, drafter=FixedDrafter(), max_contacts=1).execute_run(get_target_profile('robert'))
    assert result['stop_reason'] == 'explicit_rejection'
    assert json.loads((tmp_path/'s_fixture.json').read_text())['status'] == 'completed'


def test_rejected_draft_and_review_are_saved_before_any_send(tmp_path, monkeypatch):
    monkeypatch.setattr('src.controller.LOGS_DIR', str(tmp_path))
    prompts = []
    def generate(**kwargs):
        prompts.append(kwargs)
        if 'supported' in kwargs['schema']['properties']:
            return {'supported': False, 'issues': ['unsupported_target_claim']}
        return {'body': '<p>Deliberately unsupported synthetic claim.</p>', 'used_fact_ids': []}
    drafter = MessageDrafter(SimpleNamespace(mock_mode=False, generate_structured=generate))
    api = ScriptedClient([])
    with pytest.raises(DraftReviewError):
        RunController(api, drafter=drafter).execute_run(get_target_profile('robert'))
    raw = json.loads((tmp_path/'s_fixture.json').read_text())
    assert api.actual_sends == 0
    assert [r['stage'] for r in raw['draft_diagnostics']] == ['generation', 'review', 'generation', 'review']
    assert raw['draft_diagnostics'][0]['draft']['body'].startswith('<p>Deliberately')
    assert raw['draft_diagnostics'][1]['review']['issues'] == ['unsupported_target_claim']
    assert all(r['duration_seconds'] >= 0 for r in raw['draft_diagnostics'])
    assert 'identity (name, role, organization) needs no fact citation' in prompts[1]['system_prompt']
