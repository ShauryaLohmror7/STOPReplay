"""Complete, script-free local transcript view from a recorded simulator journal.

No network, model calls, session creation or writes to the input recording.
Message HTML is escaped source, never executable document content.
"""
import argparse
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import tempfile

from src.reporting import build_timeline


def _text(value):
    return escape(str(value)) if value is not None else "Unknown"


def _json(value):
    return '<pre>' + escape(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)) + '</pre>'


class _VisibleBody(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _bubble(label, body, *, html=False):
    if body is None:
        return f'<div class="message"><b>{_text(label)}</b><p>No text recorded.</p></div>'
    visible = str(body)
    if html:
        parser = _VisibleBody()
        parser.feed(visible)
        visible = ''.join(parser.parts)
    result = f'<div class="message"><b>{_text(label)}</b><pre>{escape(visible)}</pre></div>'
    if html:
        result += '<details><summary>Original message source (escaped)</summary><pre>' + _text(body) + '</pre></details>'
    return result


def _dialogue(opening, dialogue):
    rendered = _bubble('Target — call greeting', (opening or {}).get('persona_says'))
    for i, line in enumerate(dialogue, 1):
        rendered += f'<h4>Utterance {i} · simulated time: {_text(line.get("sent_at"))}</h4>'
        rendered += _bubble('Agent', line.get('say'))
        rendered += _bubble('Target', line.get('response', {}).get('persona_says'))
        rendered += '<details><summary>Utterance events, attachments and review</summary>' + _json(line) + '</details>'
    return rendered


def render_transcript(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('session_id'), str):
        raise ValueError('A journal with a session identity is required.')
    timeline = build_timeline(raw['session_id'], raw)
    title = f"Session {raw['session_id']}"
    body = f'<h1>{_text(title)}</h1><p>Mode: <b>{_text(timeline["mode"])}</b> · Target: {_text(timeline["target_id"])}</p>'
    body += f'<p>Status: {_text(raw.get("status"))} · Completed contacts: {_text(raw.get("touches_used"))} · Stop reason: {_text(raw.get("stop_reason"))}</p>'
    body += '<p class="notice">Recorded observations only. Official incident, hidden topic hits and own-angle qualification are unknown. Simulated time is separate from actual receipt time.</p>'
    for turn in timeline['timeline']:
        outgoing = turn['attacker']
        body += f'<section><h2>Contact {_text(turn["turn_no"])} · {_text(outgoing["channel"])}</h2>'
        body += f'<p>ID: {_text(turn["contact_id"])}<br>Simulated: {_text(turn["sent_at"])} → {_text(turn["story_time_end"])}<br>Recorded: {_text(turn["timestamp"])}</p>'
        body += '<details><summary>Sender, subject and attachment</summary>' + _json({k: outgoing[k] for k in ('sender', 'subject', 'attachment')}) + '</details>'
        if turn.get('conversation_id'):
            body += _dialogue(turn.get('opening'), turn.get('dialogue', []))
        else:
            body += _bubble('Agent', outgoing['body'], html=outgoing['channel'] == 'email')
            replies = [e for e in turn['events'] if e.get('type') == 'reply']
            if replies:
                for reply in replies:
                    body += _bubble('Target — ' + str(reply.get('channel', 'unknown channel')), reply.get('body'))
            else:
                body += _bubble('Target', turn['twin_reply'])
        body += '<details><summary>Complete contact, events and evidence</summary>' + _json(turn) + '</details></section>'
    pending = raw.get('pending')
    if pending:
        body += '<section><h2>Pending contact — delivery may be uncertain</h2><p>This is not a completed contact. Resume with its existing journal; do not resend it manually.</p>'
        call = pending.get('conversation')
        if call:
            body += f'<p>Conversation: {_text(call.get("id"))} · API count at start: {_text(call.get("start_response", {}).get("touches_used"))}</p>'
            body += _dialogue(call.get('start_response'), call.get('dialogue', []))
        body += '<details><summary>Saved pending request and acknowledged responses</summary>' + _json(pending) + '</details></section>'
    if raw.get('failure'):
        body += '<section><h2>Recorded interruption</h2>' + _json(raw['failure']) + '</section>'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; form-action &#39;none&#39;; base-uri &#39;none&#39;">'
            '<title>' + _text(title) + '</title><style>'
            'body{font:16px/1.55 system-ui,sans-serif;color:#17283b;background:#f3f5f8;margin:0 auto;padding:24px;max-width:1000px}'
            'section{background:white;border:1px solid #d5dce4;border-radius:12px;padding:20px;margin:24px 0}'
            '.notice{border-left:4px solid #786126;padding:12px;background:#fff8df}'
            '.message{padding:12px 16px;background:#eef3f8;border-radius:8px;margin:12px 0}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}details{margin:12px 0}summary{cursor:pointer;font-weight:600}'
            'h2{margin-top:0}h4{margin-bottom:4px}@media(max-width:600px){body{padding:12px}section{padding:12px}}'
            '@media print{body{background:white;padding:0}section{break-inside:auto}.notice{border:1px solid}}'
            '</style></head><body>' + body + '</body></html>')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    if args.journal.resolve() == args.output.resolve():
        parser.error('Output must not overwrite the journal.')
    html = render_transcript(json.loads(args.journal.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.transcript-', dir=args.output.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(html)
        os.replace(temp, args.output)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print(args.output.resolve())


if __name__ == '__main__':
    main()
