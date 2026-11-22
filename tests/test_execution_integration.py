import json
import pytest
from src.api.target_client import TargetClient, TargetAPIError
from src.journal_import import import_journal
from src.replay import replay_events
from stopreplay_analysis.engine import Analyzer
from stopreplay_analysis.fake import RoomFixtureAdapter


def sample_journal():
    return {'session_id': 's_import_fixture', 'turns': [
        {'turn': 1, 'message_id': 'm1', 'sent': 'Synthetic contact', 'sent_channel': 'email',
         'reply': 'Synthetic reply', 'events': [{'id': 'e1', 'type': 'reply', 'body': 'Synthetic reply'}]}]}


def test_journal_storage_analysis_end_to_end(storage):
    journal = sample_journal()
    info = import_journal(storage, journal)
    run = info['run_id']
    assert import_journal(storage, journal) == info
    events = storage.get_events(run)
    assert len(events) == 1 and 'Unverified' in events[0]['text']
    source = storage.get_source(run, events[0]['source_ref'])
    assert json.loads(source['excerpt']) == journal['turns'][0]
    # Fake deliberately says no_change for unfamiliar text. This tests the full
    # storage/analysis handoff, not a model's disclosure judgment.
    timeline = replay_events(storage, Analyzer(RoomFixtureAdapter()), run_id=run, analysis_id='v1')
    assert len(timeline) == 1 and timeline[0]['finding'] is None
    changed = sample_journal()
    changed['turns'][0]['reply'] = 'Different content'
    with pytest.raises(ValueError, match='conflicts'):
        import_journal(storage, changed)
    assert storage.get_events(run) == events
    changed = sample_journal()
    changed['turns'][0]['message_id'] = 'replacement'
    with pytest.raises(ValueError, match='position'):
        import_journal(storage, changed)
    assert storage.get_events(run) == events


def test_partial_journal_rejected_before_storage_calls():
    class NoWrites:
        def get_events(self, *args):
            raise AssertionError('Validation must happen before storage')
    bad = sample_journal()
    bad['turns'][0]['turn'] = 2
    with pytest.raises(ValueError):
        import_journal(NoWrites(), bad)


def test_call_transcript_clock_and_evidence_ledger_persist_in_postgres(storage):
    journal = sample_journal()
    journal['turns'][0].update(
        message_id='c1', conversation_id='c1', sent_channel='phone_call',
        sent_at='2026-11-23T09:00:00+01:00', story_time_end='2026-11-23T09:00:30+01:00',
        dialogue=[{'say': 'Synthetic question', 'response': {'persona_says': 'Synthetic answer', 'ended': False}}],
        evidence_context={'available_facts': [{'id': 'f1', 'source_ref': 'public1', 'claim': 'Synthetic role'}]},
        grounding={'status': 'model_review_passed', 'used_fact_ids': ['f1']})
    run = import_journal(storage, journal)['run_id']
    event = storage.get_events(run)[0]
    source = storage.get_source(run, event['source_ref'])
    assert json.loads(source['excerpt']) == journal['turns'][0]
    assert import_journal(storage, journal)['contacts'] == 1
    assert len(storage.get_events(run)) == 1


def test_retry_keeps_exact_key_body_and_is_bounded(monkeypatch):
    api = TargetClient(team_key='test')
    calls, waits = [], []
    def once(*args):
        calls.append(args)
        if len(calls) < 3:
            raise TargetAPIError('Unavailable', status_code=503)
        return {'message_id': 'm1'}
    monkeypatch.setattr(api, '_request_once', once)
    monkeypatch.setattr('src.api.target_client.time.sleep', waits.append)
    assert api._request('POST', '/sessions/s1/messages', {'body': 'fixture'}, 'durable-key')['message_id'] == 'm1'
    assert calls[0] == calls[1] == calls[2]
    assert waits == [2, 4]


@pytest.mark.parametrize('method,endpoint,key,status', [
    ('POST', '/sessions', None, 503),
    ('POST', '/sessions/s1/messages', 'key', 422),
    ('POST', '/sessions/s1/messages', 'key', 401),
])
def test_unsafe_or_permanent_requests_are_not_retried(monkeypatch, method, endpoint, key, status):
    api = TargetClient(team_key='test')
    calls = []
    def once(*args):
        calls.append(args)
        raise TargetAPIError('Fixture error', status_code=status)
    monkeypatch.setattr(api, '_request_once', once)
    with pytest.raises(TargetAPIError):
        api._request(method, endpoint, {}, key)
    assert len(calls) == 1


def test_storage_failure_after_terminal_contact_resumes_without_send(tmp_path, monkeypatch):
    from src.controller import RunController
    from src.models.schemas import TargetProfile
    from tests.test_scoring_readiness import ScriptedClient, FixedDrafter
    monkeypatch.setattr('src.controller.LOGS_DIR', str(tmp_path))
    api = ScriptedClient([[{'id': 'e1', 'type': 'attachment.opened'}]])
    profile = TargetProfile('synthetic', 'Synthetic Lead', role='Sales')
    def unavailable(state):
        raise RuntimeError('Synthetic storage outage')
    with pytest.raises(RuntimeError, match='outage'):
        RunController(api, drafter=FixedDrafter(), event_sink=unavailable).execute_run(profile)
    path = tmp_path / 's_fixture.json'
    saved = json.loads(path.read_text())
    assert saved['incident_reached'] and saved['pending'] is None
    assert saved['status'] == 'interrupted'
    api.get_session = lambda sid: {'status': 'ended', 'touches_used': 1}
    with pytest.raises(ValueError, match='storage sink'):
        RunController(api, drafter=FixedDrafter()).execute_run(profile, resume_path=path)
    imported = []
    result = RunController(api, drafter=FixedDrafter(), event_sink=lambda state: imported.extend(state['turns'])).execute_run(profile, resume_path=path)
    assert api.starts == api.actual_sends == len(api.requests) == 1
    assert len(imported) == len(result['history']) == 1
    assert json.loads(path.read_text())['status'] == 'completed'


def test_live_preflight_requires_research_or_explicit_metadata_only(monkeypatch, capsys):
    import run_live_attack
    from types import SimpleNamespace
    monkeypatch.setattr(run_live_attack, 'load_env_file', lambda: None)
    monkeypatch.setenv('REVEL8_TEAM_KEY', 'synthetic-key')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setattr('src.api.target_client.TargetClient.list_scenarios', lambda self: [
        {'id': 'practice', 'open': True, 'targets': [{'id': 'synthetic', 'name': 'Synthetic Lead', 'role': 'Sales'}]}])
    monkeypatch.setattr('src.runtime.adapter.ModelAdapter', lambda **kw: SimpleNamespace(
        mock_mode=False, api_key='synthetic', get_runtime_metadata=lambda **kw: {'mode': 'test'}))
    assert run_live_attack.main(['--target', 'synthetic', '--preflight']) == 1
    assert 'research/storage is required' in capsys.readouterr().out
    assert run_live_attack.main(['--target', 'synthetic', '--preflight', '--metadata-only']) == 0
    assert 'unverified' in capsys.readouterr().out


def test_preflight_collects_only_when_existing_facts_absent_and_closes_db(monkeypatch):
    import run_live_attack
    from types import SimpleNamespace
    from src.models.schemas import TargetProfile, Fact
    monkeypatch.setattr(run_live_attack, 'load_env_file', lambda: None)
    monkeypatch.setenv('REVEL8_TEAM_KEY', 'synthetic-key')
    monkeypatch.setenv('DATABASE_URL', 'synthetic-no-network')
    monkeypatch.setattr('src.api.target_client.TargetClient.list_scenarios', lambda self: [{'id': 'practice', 'open': True}])
    monkeypatch.setattr('src.runtime.adapter.ModelAdapter', lambda **kw: SimpleNamespace(
        mock_mode=False, api_key='synthetic', get_runtime_metadata=lambda **kw: {'mode': 'test'}))
    closed, calls = [], []
    connection = SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr('stopreplay_db.db.connect', lambda: connection)
    monkeypatch.setattr('stopreplay_db.Storage', lambda conn: SimpleNamespace(get_source=lambda *a: {'origin': 'public_web'}))
    def profile(scenario, target, **kw):
        calls.append(kw)
        facts = [Fact('f1', target, 'Sales role', 'role', 'r', 's')] if kw.get('research') else []
        return TargetProfile(target, 'Synthetic Lead', role='Sales', facts=facts)
    monkeypatch.setattr('src.bridge.profile_from_scenario', profile)
    assert run_live_attack.main(['--target', 'synthetic', '--preflight']) == 0
    assert len(calls) == 2 and calls[1]['research'] is True
    assert closed == [True]
