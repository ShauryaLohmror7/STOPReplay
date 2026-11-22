"""Synthetic API tests: no real sessions, channels, credentials or model calls."""
from datetime import datetime
import json
from types import SimpleNamespace
import pytest

from src.api.target_client import TargetClient, TargetAPIError
from src.bridge import get_target_profile
from src.contact_policy import channel_plan, contact_time, timing_plan
from src.controller import RunController
from src.draft_grounding import check_draft, fact_ledger
from src.orchestrator.strategy_planner import StrategySelector
from src.runtime.adapter import InvalidModelOutput
from src.reporting import build_timeline
from tests.test_scoring_readiness import FixedDrafter, ScriptedClient


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr('src.controller.LOGS_DIR', str(tmp_path))


def test_silence_uses_available_channels_until_budget():
    api = ScriptedClient([[] for _ in range(10)])
    api.list_channels = lambda: ['email', 'sms', 'whatsapp', 'slack', 'signal', 'telegram',
                                 'discord', 'teams_chat', 'linkedin_message', 'imessage']
    result = RunController(api, drafter=FixedDrafter(), channel_mode='coverage').execute_run(get_target_profile('julius'))
    assert result['touches_used'] == 10
    assert len({t['sent_channel'] for t in result['history']}) == 10
    assert result['stop_reason'] == 'contact_budget'


def test_one_reply_does_not_end_session_but_explicit_stop_does():
    api = ScriptedClient([[{'id': 'e1', 'type': 'reply', 'body': 'Could you explain the request?'}],
                          [{'id': 'e2', 'type': 'reply', 'body': 'Stop contacting me.'}]])
    result = RunController(api, drafter=FixedDrafter()).execute_run(get_target_profile('julius'))
    assert result['touches_used'] == 2
    assert result['stop_reason'] == 'explicit_rejection'


def test_monday_friday_is_sent_and_reported_not_real_time(tmp_path):
    api = ScriptedClient([[], []])
    drafter = FixedDrafter()
    result = RunController(api, drafter=drafter, timing='monday-friday',
                           story_start='2026-11-23T09:00:00+01:00').execute_run(get_target_profile('julius'))
    assert [datetime.fromisoformat(r['story_time']).weekday() for r in api.requests] == [0, 4]
    assert '2026-11-27T09:00:00+01:00' in drafter.contexts[1]
    raw = json.loads((tmp_path / 's_fixture.json').read_text())
    timeline = build_timeline(result['session_id'], raw)
    assert timeline['timeline'][1]['sent_at'] == api.requests[1]['story_time']
    assert timeline['timeline'][1]['timestamp'] != timeline['timeline'][1]['sent_at']


def test_timing_requires_offset_and_monday():
    for start in ['2026-11-23T09:00:00', '2026-11-24T09:00:00+01:00']:
        with pytest.raises(ValueError):
            timing_plan('monday-friday', start)
    plan = timing_plan('spaced', '2026-11-23T09:00:00+01:00')
    value = contact_time(plan, [{'sent_at': plan['start'], 'story_time_end': plan['start'], 'reply': 'Maybe next week.'}])
    assert datetime.fromisoformat(value).day == 30


def test_discovery_rejects_unknown_push_channels():
    assert channel_plan(['mfa_push', 'invented', {'id': 'email'}], 'invented') == ['email']
    with pytest.raises(ValueError):
        channel_plan(['mfa_push'], 'email')


class CallAPI(TargetClient):
    def __init__(self, loss=None, objective_at=None, hangup_at=None):
        super().__init__(team_key='synthetic')
        self.loss, self.objective_at, self.hangup_at = loss, objective_at, hangup_at
        self.cache, self.calls, self.counts = {}, [], {'start': 0, 'turn': 0, 'end': 0}
        self.ended = False
    def list_channels(self):
        return ['phone_call']
    def start_session(self, *args, **kwargs):
        return {'session_id': 's_call', 'touch_budget': 1, 'touches_used': 0}
    def get_session(self, sid):
        return {'status': 'ended' if self.counts['start'] else 'active', 'touches_used': self.counts['start']}
    def _request(self, method, endpoint, payload=None, idempotency_key=None, timeout=120):
        kind = 'start' if endpoint.endswith('/conversations') else 'turn' if endpoint.endswith('/turns') else 'end'
        self.calls.append((kind, payload, idempotency_key))
        if idempotency_key in self.cache:
            assert self.cache[idempotency_key][0] == payload
            return self.cache[idempotency_key][1]
        self.counts[kind] += 1
        if kind == 'start':
            result = {'conversation_id': 'c_fixture', 'status': 'answered', 'persona_says': 'Hello?', 'touches_used': 1}
        elif kind == 'turn':
            n = self.counts[kind]
            result = {'persona_says': 'Tell me more.', 'turns_used': n, 'ended': n == self.hangup_at,
                      'events': [{'id': 'e_open', 'type': 'attachment.opened', 'conversation_id': 'c_fixture'}]
                      if n == self.objective_at else []}
        else:
            result = {}
            self.ended = True
        if idempotency_key:
            self.cache[idempotency_key] = (payload, result)
        if self.loss == kind:
            self.loss = None
            raise TargetAPIError('Synthetic lost response')
        return result


def test_ten_call_utterances_cost_one_touch_and_keep_whole_transcript(tmp_path):
    api, drafter = CallAPI(), FixedDrafter()
    result = RunController(api, drafter=drafter, timing='spaced',
                           story_start='2026-11-23T09:00:00+01:00').execute_run(get_target_profile('julius'))
    assert result['touches_used'] == 1
    assert api.counts == {'start': 1, 'turn': 10, 'end': 1}
    turn = result['history'][0]
    assert turn['message_id'] == turn['conversation_id'] == 'c_fixture'
    assert len(turn['dialogue']) == 10
    assert 'Hello?' in drafter.contexts[0] and 'Tell me more.' in drafter.contexts[1]
    assert all(datetime.fromisoformat(line['sent_at']) > datetime.fromisoformat(turn['sent_at']) for line in turn['dialogue'])
    assert turn['evidence_context']['available_facts']
    raw = json.loads((tmp_path / 's_call.json').read_text())
    assert len(build_timeline('s_call', raw)['timeline'][0]['dialogue']) == 10


def test_agent_closing_call_is_recorded_without_sending_local_control_fields():
    class ClosingDrafter(FixedDrafter):
        def draft_contact(self, *args, **kwargs):
            return {**super().draft_contact(*args, **kwargs), 'end_conversation_after_send': True}
    api = CallAPI()
    result = RunController(api, drafter=ClosingDrafter()).execute_run(get_target_profile('julius'))
    assert api.counts == {'start': 1, 'turn': 1, 'end': 1}
    assert result['history'][0]['conversation_stop'] == 'agent_closed'
    assert result['history'][0]['dialogue'][0]['end_after_send'] is True
    assert not result['incident_reached']
    payload = next(payload for kind, payload, key in api.calls if kind == 'turn')
    assert 'end_after_send' not in payload and 'grounding' not in payload


@pytest.mark.parametrize('loss', ['start', 'turn', 'end'])
def test_call_resume_reuses_saved_key_body_and_clock(tmp_path, loss):
    api = CallAPI(loss=loss, objective_at=1)
    profile = get_target_profile('julius')
    controller = RunController(api, drafter=FixedDrafter(), timing='spaced', story_start='2026-11-23T09:00:00+01:00')
    with pytest.raises(TargetAPIError):
        controller.execute_run(profile)
    result = controller.execute_run(profile, resume_path=tmp_path / 's_call.json')
    assert result['incident_reached']
    assert api.counts['start'] == api.counts['turn'] == 1
    requests = [(payload, key) for kind, payload, key in api.calls if kind == loss]
    assert len(requests) == 2 and requests[0] == requests[1]


@pytest.mark.parametrize('argument', ['objective_at', 'hangup_at'])
def test_calls_stop_on_objective_or_hangup(argument):
    api = CallAPI(**{argument: 2})
    result = RunController(api, drafter=FixedDrafter()).execute_run(get_target_profile('julius'))
    assert api.counts['turn'] == 2
    assert result['incident_reached'] == (argument == 'objective_at')


def test_draft_cannot_cite_unknown_facts_or_pass_failed_review():
    profile = get_target_profile('julius')
    hook = StrategySelector().build_hook('LANE_1_ENTERPRISE_RFP', profile)
    ledger = fact_ledger(profile, hook)
    adapter = SimpleNamespace(generate_structured=lambda **kw: {'supported': False, 'issues': ['Unsupported target claim']})
    for result in [{'body': 'You studied at Stanford.', 'used_fact_ids': ['invented']},
                   {'body': 'You studied at Stanford.', 'used_fact_ids': []}]:
        with pytest.raises(InvalidModelOutput):
            check_draft(adapter, result, ledger, profile, {}, '')


def test_collection_does_not_attribute_a_copresent_persons_bio():
    from stopreplay_collect.extract import extract_facts
    facts = extract_facts([{'source_ref': 's', 'origin': 'public_web', 'url': 'https://example.invalid/team',
        'excerpt': 'Synthetic Lead and Other Person are on this page. Other Person graduated from Stanford University.\n'
                   'Other Person is based in Berlin. Synthetic Lead spoke at the event.'}], 'synthetic', name='Synthetic Lead')
    assert all(not f.assertable for f in facts if f.claim.startswith(('education:', 'based_in:', 'public_appearance:')))


def test_disclosure_fields_are_recorded_without_assuming_a_win():
    from src.session_evidence import summarize_events
    event = {'id': 'e_form', 'type': 'page.submitted', 'page_id': 'p1',
             'fields': ['email', 'internal_tool'], 'values': {'email': 'person@example.invalid', 'internal_tool': 'A public product'}}
    evidence = summarize_events([event], trusted_transport=True)
    assert [v['kind'] for v in evidence['information_observations']] == ['basic_detail', 'unclassified_information']
    assert not evidence['verified_objective']
    assert all(not v['disclosure_established'] for v in evidence['information_observations'])


def test_duplicate_claim_does_not_make_ineligible_fact_assertable():
    from dataclasses import replace
    profile = get_target_profile('julius')
    profile.facts.append(replace(profile.facts[0], id='wrong', subject='other', assertable=False))
    hook = StrategySelector().build_hook('LANE_1_ENTERPRISE_RFP', profile)
    assert 'wrong' not in [f['id'] for f in fact_ledger(profile, hook)]


def test_second_eval_for_same_target_requires_resume(tmp_path):
    api = ScriptedClient([[{'id': 'e1', 'type': 'attachment.opened'}]])
    controller = RunController(api, drafter=FixedDrafter())
    controller.execute_run(get_target_profile('julius'), practice=False)
    with pytest.raises(ValueError, match='already has a local scoring session'):
        controller.execute_run(get_target_profile('julius'), practice=False)
    assert api.starts == 1


def test_complete_conversation_and_evidence_survive_storage_import():
    from src.journal_import import import_journal
    api = CallAPI(objective_at=1)
    imported = []
    class MemoryStorage:
        def get_events(self, run):
            return []
        def register_source(self, source):
            imported.append(source)
        def import_event(self, event):
            pass
    controller = RunController(api, drafter=FixedDrafter(),
                               event_sink=lambda state: import_journal(MemoryStorage(), state))
    controller.execute_run(get_target_profile('julius'))
    turn = json.loads(imported[0]['excerpt'])
    assert turn['conversation_id'] == 'c_fixture'
    assert len(turn['dialogue']) == 1
    assert turn['evidence_context']['available_facts']


def test_progress_identifies_mode_and_stage_without_outbound_contents():
    progress = []
    api = ScriptedClient([[{'id': 'e1', 'type': 'attachment.opened'}]])
    RunController(api, drafter=FixedDrafter(), progress=progress.append).execute_run(get_target_profile('julius'))
    assert any('Opening practice session' in line for line in progress)
    assert any('Preparing contact 1/10' in line for line in progress)
    assert any('Sending email contact' in line for line in progress)
    assert any('Recorded contact 1/10' in line for line in progress)
    assert 'Session finished: objective_evidence' in progress[-1]
    assert all('Synthetic fixture contact' not in line for line in progress)


def test_keyboard_interrupt_preserves_pending_request(tmp_path):
    class InterruptedClient(ScriptedClient):
        def send_contact(self, **kwargs):
            raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        RunController(InterruptedClient([]), drafter=FixedDrafter()).execute_run(get_target_profile('julius'))
    state = json.loads((tmp_path / 's_fixture.json').read_text())
    assert state['status'] == 'interrupted'
    assert state['pending']['idempotency_key']
    assert state['touches_used'] == 0
