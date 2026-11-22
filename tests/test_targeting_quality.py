from datetime import date
import json
from types import SimpleNamespace

import pytest
from src.bridge import profile_from_scenario
from src.controller import RunController
from src.models.schemas import Fact, TargetProfile
from src.orchestrator.strategy_planner import StrategySelector
from src.orchestrator.topic_ranking import rank_topics
from tests.test_scoring_readiness import ScriptedClient, FixedDrafter

TODAY = date(2026, 11, 22)


@pytest.mark.parametrize('wording', ['go-to-market', 'go to market', 'go–to–market', 'GTM'])
def test_organizer_business_role_matches_without_inventing_public_facts(wording):
    p = profile_from_scenario({'id': 'practice', 'company': 'revel8', 'targets': [
        {'id': 'julius', 'name': 'Julius Muth', 'role': f'Co-Founder & Co-CEO, revel8 (business and {wording})'}]}, 'julius')
    result = rank_topics(p, as_of=TODAY)
    assert result['selected_lane'] == 'LANE_1_ENTERPRISE_RFP'
    assert result['selection_basis'] == 'organizer_role_baseline'
    assert result['candidates'][0]['evidence'] == []
    assert p.get_assertable_claims() == []


def test_ceo_alone_does_not_invent_a_sales_role():
    result = rank_topics(TargetProfile('synthetic', 'Synthetic Person', role='CEO'), as_of=TODAY)
    assert result['role_baseline'] is None


def profile():
    return TargetProfile('synthetic', 'Synthetic Research Lead', role='Sales lead', facts=[
        Fact('f1', 'synthetic', 'Published a research paper on benchmarks', 'project', 'r', 'paper', confidence=.95),
        Fact('f2', 'synthetic', 'Sales leadership', 'role', 'r', 'bio', confidence=.95)])


def sources(paper_date='2026-11-01'):
    return {'paper': {'observed_on': paper_date}, 'bio': {'observed_on': '2026-10-01'}}


def test_current_specific_evidence_beats_broad_role_without_claiming_bonus():
    result = rank_topics(profile(), source_metadata=sources(), as_of=TODAY)
    assert result['selected_lane'] == 'LANE_9_CREATIVE_CONTRIBUTOR_RELEASE'
    assert result['candidates'][0]['alternative_to_role_baseline'] is True
    assert result['own_angle_status'] == 'unverified'
    assert result['candidates'][0]['evidence'][0]['source_ref'] == 'paper'


def test_stale_and_unknown_source_dates_are_not_current():
    result = rank_topics(profile(), source_metadata=sources('2020-01-01'), as_of=TODAY)
    assert result['selected_lane'] == 'LANE_1_ENTERPRISE_RFP'
    result = rank_topics(profile(), source_metadata={'paper': {}, 'bio': {}}, as_of=TODAY)
    assert all(e['freshness'] == 'unknown' for c in result['candidates'] for e in c['evidence'])


@pytest.mark.parametrize('change,reason', [
    ({'status': 'refuted'}, 'inactive_or_not_assertable'),
    ({'sensitivity': 'private'}, 'not_public'),
    ({'confidence': .1}, 'insufficient_confidence'),
    ({'subject': 'other'}, 'different_subject'),
    ({'assertable': False}, 'inactive_or_not_assertable')])
def test_weak_facts_cannot_drive_selection(change, reason):
    p = profile()
    for key, value in change.items():
        setattr(p.facts[0], key, value)
    result = rank_topics(p, source_metadata=sources(), as_of=TODAY)
    assert result['selected_lane'] == 'LANE_1_ENTERPRISE_RFP'
    assert reason in result['excluded_facts'][0]['reasons']


def test_duplicate_source_does_not_multiply_support():
    p = profile()
    before = rank_topics(p, source_metadata=sources(), as_of=TODAY)
    for i in range(20):
        p.facts.append(Fact(f'extra{i}', 'synthetic', 'Research paper contribution', 'project', 'r', 'paper', confidence=.95))
    after = rank_topics(p, source_metadata=sources(), as_of=TODAY)
    assert before['candidates'][0]['score'] == after['candidates'][0]['score']


def test_reaction_updates_relevance_without_treating_question_as_a_hit():
    p = profile()
    initial = rank_topics(p, source_metadata=sources(), as_of=TODAY)
    questions = [{'lane_id': initial['selected_lane'], 'message_id': 'm1', 'reply': 'What is the deadline?'}]
    assert rank_topics(p, source_metadata=sources(), history=questions, as_of=TODAY)['candidates'] == initial['candidates']
    rejection = [dict(questions[0], reply='That topic is not relevant to our team.')]
    result = rank_topics(p, source_metadata=sources(), history=rejection, as_of=TODAY)
    assert result['selected_lane'] == 'LANE_1_ENTERPRISE_RFP'
    rejected = next(c for c in result['candidates'] if c['lane_id'] == initial['selected_lane'])
    assert rejected['score'] == 0 and rejected['rejection']['contact_id'] == 'm1'


def test_controller_reassesses_once_and_preserves_sender(tmp_path, monkeypatch):
    monkeypatch.setattr('src.controller.LOGS_DIR', str(tmp_path))
    api = ScriptedClient([
        [{'id': 'e1', 'type': 'reply', 'body': 'This is not relevant to our team.', 'channel': 'email'}],
        [{'id': 'e2', 'type': 'attachment.opened'}]])
    # Fix dates for this synthetic experiment; it is not a live targeting score.
    selector = StrategySelector(source_metadata=sources())
    original = selector.assess
    selector.assess = lambda p, history=(), as_of=None: original(p, history, as_of=TODAY)
    result = RunController(api, selector, FixedDrafter()).execute_run(profile())
    turns = result['history']
    assert turns[0]['lane_id'] == 'LANE_9_CREATIVE_CONTRIBUTOR_RELEASE'
    assert turns[1]['lane_id'] == 'LANE_1_ENTERPRISE_RFP'
    assert turns[0]['sender'] == turns[1]['sender']
    saved = json.loads((tmp_path/'s_fixture.json').read_text())
    assert saved['topic_switches'] == 1
    assert saved['topic_assessment']['own_angle_status'] == 'unverified'


def test_inferred_collection_attributes_are_not_assertable():
    from stopreplay_collect.extract import extract_facts
    source = {'origin': 'public_web', 'source_ref': 's', 'url': 'https://example.invalid/team',
              'excerpt': 'Synthetic Lead is co-founder with Other Person. Contact info@example.invalid. Passionate about AI.',
              'locator': 'Team'}
    facts = extract_facts([source], 'x', name='Synthetic Lead', org_domains=['example.invalid'])
    for fact in facts:
        if fact.claim.startswith(('target_email:', 'colleague_sender:', 'interest:', 'colleague:')):
            assert fact.assertable is False


@pytest.mark.parametrize('value', [True, float('nan'), float('inf'), -.1, 1.1, .5])
def test_invalid_confidence_is_excluded_from_ranking_and_drafting(value):
    p = profile()
    p.facts[0].confidence = value
    result = rank_topics(p, source_metadata=sources(), as_of=TODAY)
    assert result['excluded_facts'][0]['reasons'] == ['insufficient_confidence']
    assert p.facts[0].claim not in p.get_assertable_claims()


@pytest.mark.parametrize('date_value,reason', [
    ('2027-01-01', 'future_source_date'), ('not-a-date', 'invalid_source_date')])
def test_bad_source_dates_cannot_supply_topic_support(date_value, reason):
    result = rank_topics(profile(), source_metadata=sources(date_value), as_of=TODAY)
    assert reason in result['excluded_facts'][0]['reasons']


def test_missing_source_and_superseded_facts_are_withheld():
    p = profile()
    result = rank_topics(p, source_metadata={'bio': {}}, as_of=TODAY)
    assert 'unresolved_source' in result['excluded_facts'][0]['reasons']
    p.facts[0].superseded_by = 'replacement'
    assert p.facts[0].claim not in p.get_assertable_claims()


def test_controller_withholds_source_rejections_from_drafter(tmp_path, monkeypatch):
    monkeypatch.setattr('src.controller.LOGS_DIR', str(tmp_path))
    p = profile()
    captured = []
    class CaptureDrafter(FixedDrafter):
        def draft_contact(self, hook, profile, **kw):
            captured.extend(profile.get_assertable_claims())
            return super().draft_contact(hook, profile, **kw)
    api = ScriptedClient([[{'id': 'e1', 'type': 'attachment.opened'}]])
    selector = StrategySelector(source_metadata={'bio': {}})
    RunController(api, selector, CaptureDrafter()).execute_run(p)
    assert p.facts[0].claim not in captured
    assert p.facts[1].claim in captured
    assert len(p.facts) == 2  # Original source snapshot remains intact.
