from html.parser import HTMLParser
import json
import pytest
from src.transcript_export import render_transcript, main


def fixture():
    return {'session_id': 's_fixture', 'target_id': 'synthetic', 'mode': 'practice',
            'status': 'interrupted', 'touches_used': 1, 'turns': [
                {'turn': 1, 'message_id': 'm1', 'sent_channel': 'email',
                 'sent': '<p>Hello &amp; welcome.</p>', 'sent_subject': 'Fixture',
                 'sent_at': '2026-11-23T09:00:00+01:00', 'timestamp': '2026-11-22T10:00:00Z',
                 'events': [{'id': 'e1', 'type': 'reply', 'channel': 'email', 'body': 'First complete reply'},
                            {'id': 'e2', 'type': 'reply', 'channel': 'sms', 'body': 'Second complete reply'}]}]}


def test_complete_replies_and_distinct_clocks_are_exported():
    html = render_transcript(fixture())
    for expected in ['First complete reply', 'Second complete reply', '2026-11-23T09:00:00+01:00',
                     '2026-11-22T10:00:00Z', 'practice', 'Official incident', 'Hello &amp; welcome.']:
        assert expected in html


def test_every_call_utterance_and_pending_call_are_included():
    raw = fixture()
    lines = [{'say': f'Agent utterance {i}', 'response': {'persona_says': f'Target response {i}'}}
             for i in range(1, 11)]
    raw['turns'].append({'turn': 2, 'message_id': 'c1', 'conversation_id': 'c1', 'sent_channel': 'phone_call',
                         'opening': {'persona_says': 'Initial greeting'}, 'dialogue': lines, 'events': []})
    raw['pending'] = {'request': {}, 'conversation': {'id': 'c2',
        'start_response': {'persona_says': 'Pending greeting', 'touches_used': 3},
        'dialogue': [{'say': 'Already acknowledged question', 'response': {'persona_says': 'Acknowledged answer'}}]}}
    html = render_transcript(raw)
    for i in range(1, 11):
        assert f'Agent utterance {i}' in html and f'Target response {i}' in html
    assert 'Initial greeting' in html and 'Pending greeting' in html
    assert 'Acknowledged answer' in html and 'delivery may be uncertain' in html


def test_recorded_html_and_metadata_cannot_execute_or_load_resources():
    raw = fixture()
    raw['session_id'] = '</title><script>alert(1)</script>'
    raw['turns'][0]['sent'] = '<img src="https://example.invalid/track" onerror="alert(1)"><script>evil()</script>'
    raw['turns'][0]['events'][0]['body'] = '</pre><iframe src="https://example.invalid"></iframe>'
    class Tags(HTMLParser):
        def __init__(self):
            super().__init__(); self.tags = []; self.attrs = []
        def handle_starttag(self, tag, attrs):
            self.tags.append(tag); self.attrs.extend(attrs)
    parsed = Tags(); parsed.feed(render_transcript(raw))
    assert not {'script', 'iframe', 'img', 'form'} & set(parsed.tags)
    assert not any(key.lower().startswith('on') for key, value in parsed.attrs)
    assert ('http-equiv', 'Content-Security-Policy') in parsed.attrs


def test_cli_preserves_input_and_refuses_to_overwrite_it(tmp_path):
    source, target = tmp_path/'recording.json', tmp_path/'report.html'
    original = json.dumps(fixture())
    source.write_text(original)
    main([str(source), '--output', str(target)])
    assert target.read_text().startswith('<!doctype html>')
    assert source.read_text() == original
    with pytest.raises(SystemExit):
        main([str(source), '--output', str(source)])
    assert source.read_text() == original
