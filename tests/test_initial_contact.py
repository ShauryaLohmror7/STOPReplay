from types import SimpleNamespace
import json
import pytest
from src.models.schemas import TargetProfile
from src.orchestrator.strategy_planner import StrategySelector
from src.orchestrator.drafter import MessageDrafter
from src.runtime.adapter import InvalidModelOutput, ProviderError


def inputs():
    p = TargetProfile('synthetic', 'Synthetic Lead', role='CTO', organization='Synthetic Company')
    return p, StrategySelector().build_hook('LANE_3_CVE_ASYNC_LEAK', p)


def test_live_model_selects_intent_but_cannot_add_unsupported_claims():
    p, hook = inputs()
    calls, audit = [], []
    def generate(**kwargs):
        calls.append(kwargs)
        return {'intent': 'review_attachment', 'tone': 'direct'}
    result = MessageDrafter(SimpleNamespace(mock_mode=False, generate_structured=generate), audit=audit.append).draft_contact(hook, p)
    assert len(calls) == 1
    assert result['attachment'] == hook.attachment
    assert 'identified' not in result['body'] and 'discovered' not in result['body']
    assert result['grounding']['status'] == 'constrained_identity_only'
    assert result['used_fact_ids'] == []
    assert audit[0]['delivery'] == 'not_submitted_at_generation'


@pytest.mark.parametrize('plan', [
    {'intent': 'review_attachment', 'tone': 'direct', 'body': 'You use a vulnerable system'},
    {'intent': 'invented', 'tone': 'direct'}, {'intent': 'review_attachment', 'tone': 'invented'},
])
def test_freeform_or_unknown_plan_is_rejected(plan):
    p, hook = inputs()
    drafter = MessageDrafter(SimpleNamespace(mock_mode=False, generate_structured=lambda **kw: plan))
    with pytest.raises(InvalidModelOutput):
        drafter.draft_contact(hook, p)


def test_provider_failure_cannot_become_a_rendered_message():
    p, hook = inputs()
    def fail(**kwargs):
        raise ProviderError('Synthetic failure')
    with pytest.raises(ProviderError):
        MessageDrafter(SimpleNamespace(mock_mode=False, generate_structured=fail)).draft_contact(hook, p)


def test_declared_identity_is_escaped_in_email():
    p, hook = inputs()
    p.name = '<script>untrusted</script>'
    draft = MessageDrafter(SimpleNamespace(mock_mode=False, generate_structured=lambda **kw: {
        'intent': 'ask_permission', 'tone': 'warm'})).draft_contact(hook, p)
    assert '<script>' not in draft['body'] and '&lt;script&gt;' in draft['body']
    assert draft['attachment'] is None


def test_no_evidence_call_answers_are_constrained_and_repetition_closes_call():
    p, hook = inputs()
    hook.channel = 'phone_call'
    drafter = MessageDrafter(SimpleNamespace(mock_mode=False, generate_structured=lambda **kw: {
        'intent': 'explain_purpose', 'tone': 'direct'}))
    story = {'discussion_topic': 'general asynchronous WebSocket reliability'}
    context = {'conversation': [{'say': 'An earlier introduction.'}], 'persona_says': 'What is the topic?'}
    first = drafter.draft_contact(hook, p, context=json.dumps(context), story=story)
    assert 'not reporting a verified finding' in first['body']
    assert '<p>' not in first['body'] and 'end_conversation_after_send' not in first
    context['conversation'].append({'say': first['body']})
    second = drafter.draft_contact(hook, p, context=json.dumps(context), story=story)
    assert second['end_conversation_after_send'] is True
    assert second['attachment'] is None and second['body'] != first['body']
    assert second['grounding']['plan']['intent'] == 'close_politely'


def test_call_can_acknowledge_unknown_without_inventing_answer():
    p, hook = inputs()
    hook.channel = 'phone_call'
    drafter = MessageDrafter(SimpleNamespace(mock_mode=False, generate_structured=lambda **kw: {
        'intent': 'acknowledge_unknown', 'tone': 'direct'}))
    result = drafter.draft_contact(hook, p, context='{}')
    assert "don't have verified information" in result['body']
    assert result['attachment'] is None
