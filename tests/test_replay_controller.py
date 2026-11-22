"""Analysis/storage handoff and resume; real DB checks use the existing fixture."""
from copy import deepcopy

import pytest
from stopreplay_analysis.engine import Analyzer
from stopreplay_analysis.fake import RoomFixtureAdapter
from src.replay import replay_events


class CountingAdapter(RoomFixtureAdapter):
    def __init__(self):
        self.calls = []
    def generate(self, request):
        self.calls.append(request.event.event_id)
        return super().generate(request)


class MemoryBoundary:
    """Storage protocol fake; real SQL behavior is tested separately below."""
    def __init__(self):
        self.events = [
            dict(run_id='demo', event_id='e1', sequence=10, source_ref='a', text='The demo is in Room A.'),
            dict(run_id='demo', event_id='e2', sequence=20, source_ref='b', text='Correction: the demo is in Room B.'),
            dict(run_id='demo', event_id='e3', sequence=30, source_ref='c', text='Unrelated fixture text.'),
        ]
        self.results = {}
        self.fail_event = None
    def current_checkpoint(self, run_id, analysis_id):
        return len(self.results.get(analysis_id, []))
    def get_results(self, run_id, analysis_id):
        return deepcopy(self.results.get(analysis_id, []))
    def get_events(self, run_id):
        return deepcopy(self.events)
    def get_analysis_context(self, run_id, analysis_id, before_sequence):
        return {'events': [e for e in self.events if e['sequence'] < before_sequence],
                'findings': [r['finding'] for r in self.results.get(analysis_id, []) if r['finding']]}
    def commit_turn(self, run_id, analysis_id, turn_no, event_id, result, finding, expected_checkpoint):
        assert expected_checkpoint == self.current_checkpoint(run_id, analysis_id)
        assert turn_no == expected_checkpoint + 1
        if event_id == self.fail_event:
            raise RuntimeError('Synthetic transaction failure')
        self.results.setdefault(analysis_id, []).append(dict(result, finding=finding))
    def get_timeline(self, run_id, analysis_id, as_of_turn):
        return deepcopy(self.results.get(analysis_id, [])[:as_of_turn])


def test_replay_resume_versions_and_no_change():
    storage, adapter = MemoryBoundary(), CountingAdapter()
    storage.fail_event = 'e2'
    with pytest.raises(RuntimeError):
        replay_events(storage, Analyzer(adapter), run_id='demo', analysis_id='v1')
    assert storage.current_checkpoint('demo', 'v1') == 1
    storage.fail_event = None
    result = replay_events(storage, Analyzer(adapter), run_id='demo', analysis_id='v1')
    assert [r['outcome'] for r in result] == ['new', 'revision', 'no_change']
    assert result[1]['finding']['revises'] == result[0]['finding']['finding_id']
    assert adapter.calls == ['e1', 'e2', 'e2', 'e3']
    assert replay_events(storage, Analyzer(adapter), run_id='demo', analysis_id='v1') == result
    assert adapter.calls == ['e1', 'e2', 'e2', 'e3']
    replay_events(storage, Analyzer(adapter), run_id='demo', analysis_id='v2')
    assert storage.get_results('demo', 'v1') == result
    assert adapter.calls[-3:] == ['e1', 'e2', 'e3']


def test_replay_database_history(storage):
    from stopreplay_db.fixture import import_room_fixture
    import_room_fixture(storage)
    adapter = CountingAdapter()
    timeline = replay_events(storage, Analyzer(adapter), run_id='demo', analysis_id='integrated-v1')
    assert len(timeline) == 2
    assert timeline[0]['superseded'] and not timeline[1]['superseded']
    earlier = storage.get_timeline('demo', 'integrated-v1', 1)
    assert len(earlier) == 1 and not earlier[0]['superseded']
    assert 'Room A' in earlier[0]['finding']['statement']
    replay_events(storage, Analyzer(adapter), run_id='demo', analysis_id='integrated-v1')
    assert adapter.calls == ['e1', 'e2']
