"""Idempotent journal ingestion through existing source/event storage interfaces.

Recorded JSON never establishes authenticated outcomes, even for a live journal.
The full original contact is preserved; interpreted findings remain separate.
"""
import hashlib
import json
from contextlib import nullcontext


def import_journal(storage, journal, *, run_id=None):
    sid = journal.get('session_id')
    if not isinstance(sid, str) or not sid.strip() or not isinstance(journal.get('turns'), list):
        raise ValueError('A session identity and contact list are required.')
    run_id = run_id or 'journal:' + sid
    prepared, identities = [], set()
    for position, turn in enumerate(journal['turns'], 1):
        mid = turn.get('message_id')
        if not isinstance(mid, str) or not mid or mid in identities or turn.get('turn') != position:
            raise ValueError('Contacts need unique message IDs and contiguous recorded positions.')
        identities.add(mid)
        original = json.dumps(turn, sort_keys=True, ensure_ascii=False, allow_nan=False)
        source_ref = f'journal:{sid}:{mid}'
        text = ('Unverified simulator contact recording. Official outcome unavailable.\n'
                f'Sent on {turn.get("sent_channel", "unknown")}:\n{turn.get("sent", "")}\n'
                f'Recorded reply:\n{turn.get("reply") or "No reply recorded."}\n'
                'Original contact JSON:\n' + original)
        event = {'run_id': run_id, 'event_id': mid, 'sequence': position,
                 'source_ref': source_ref, 'text': text,
                 'content_hash': hashlib.sha256(text.encode()).hexdigest()}
        source = {'run_id': run_id, 'source_ref': source_ref, 'origin': 'simulator_event',
                  'locator': f'session {sid}, message {mid}', 'excerpt': original,
                  'publisher': 'local journal; unverified recording',
                  'content_sha256': hashlib.sha256(original.encode()).hexdigest(),
                  'simulator_ref': {'session_id': sid, 'message_id': mid}}
        prepared.append((source, event))
    connection = getattr(storage, 'conn', None)
    with connection.transaction() if connection is not None else nullcontext():
        existing = {e['event_id']: e for e in storage.get_events(run_id)}
        positions = {e['sequence']: e['event_id'] for e in existing.values()}
        for source, event in prepared:
            if positions.get(event['sequence'], event['event_id']) != event['event_id']:
                raise ValueError('Journal position already belongs to another contact.')
            previous = existing.get(event['event_id'])
            if previous and any(previous.get(k) != event[k] for k in ('sequence', 'source_ref', 'text', 'content_hash')):
                raise ValueError('Journal contact conflicts with preserved history.')
            storage.register_source(source)
            storage.import_event(event)
    return {'run_id': run_id, 'contacts': len(prepared), 'verification': 'unverified_recording'}


def main():
    import argparse
    from stopreplay_db import Storage, db
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal')
    parser.add_argument('--run')
    args = parser.parse_args()
    with open(args.journal) as stream:
        journal = json.load(stream)
    with db.connect() as connection:
        print(json.dumps(import_journal(Storage(connection), journal, run_id=args.run)))


if __name__ == '__main__':
    main()
