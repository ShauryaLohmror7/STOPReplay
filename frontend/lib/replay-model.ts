// Local presentation fixture only. These are not shared backend contracts.
export type Operation = { service: 'model' | 'storage' | 'simulator'; status: 'ok' | 'recovered' | 'error'; detail: string; code?: string }
export type Turn = {
  id: string; time: string; label: string; channel: string; sender: string;
  direction: 'outbound' | 'system'; body: string; reaction: string; reply?: string;
  touches: number; marker?: 'incident' | 'correction';
  finding: { id: string; title: string; kind: 'Observation' | 'Inference'; quote: string; source: string; uncertainty: string; previous?: number };
  reasoning: { lane: string; topic: string; match: string; pushback: string; adaptation: string; limitation: string };
  craft: { kind: 'email' | 'page' | 'record'; title: string; text: string; footer: string };
  ops: Operation[];
}
const context = {lane:'Event coordination', topic:'Conference logistics',match:'Scenario topic matched',pushback:'No pushback recorded yet.',adaptation:'Initial contact uses the supplied conference context.',limitation:'A topic match is scenario context, not a proven cause of the outcome.'}
const roomA = {id:'f-room-a',title:'The supplied agenda lists Room A.',kind:'Observation' as const,quote:'Design systems workshop — 10:00, Room A.',source:'agenda-v1 · line 12',uncertainty:'The agenda establishes a room assignment, not attendance or trust.'}
export const turns: readonly Turn[] = [
  {id:'t01',time:'09:41:02',label:'First contact',channel:'Email',sender:'Conference desk · simulated',direction:'outbound',body:'Hello Nora, the workshop is listed at 10:00 in Room A. Your arrival preferences can be checked in the session page.',reaction:'Silence',touches:1,finding:roomA,reasoning:context,
   craft:{kind:'email',title:'Your workshop details',text:'The design systems workshop is scheduled for 10:00 in Room A. Review your session details when convenient.',footer:'Conference desk · synthetic message'},
   ops:[{service:'storage',status:'ok',detail:'Source agenda-v1 preserved.'},{service:'model',status:'ok',detail:'Finding f-room-a references agenda-v1.'},{service:'simulator',status:'ok',detail:'Contact recorded. No reply within the sample observation window.'}]},
  {id:'t02',time:'09:43:18',label:'Pushback',channel:'Chat',sender:'Conference desk · simulated',direction:'outbound',body:'Is there anything about the workshop schedule you would like us to confirm?',reaction:'Reply',reply:'I only use the published event agenda. Please confirm the room before I open anything.',touches:2,
   finding:{id:'f-verification',title:'Nora asks for source verification before opening a page.',kind:'Observation',quote:'Please confirm the room before I open anything.',source:'reply-t02 · message 1',uncertainty:'This is one recorded response, not a stable personality classification.'},
   reasoning:{...context,pushback:'The target requests an official source.',adaptation:'The recorded plan is to verify the schedule before making a follow-up contact.'},
   craft:{kind:'record',title:'A request to verify',text:'“I only use the published event agenda. Please confirm the room before I open anything.”',footer:'Incoming chat · Nora Weiss · 09:43:18'},
   ops:[{service:'simulator',status:'ok',detail:'Reply attached to contact 02.'},{service:'storage',status:'ok',detail:'Reply and source pointer committed.'},{service:'model',status:'ok',detail:'Verification request recorded as an observation.'}]},
  {id:'t03',time:'09:46:05',label:'Link opened',channel:'Email',sender:'Conference desk · simulated',direction:'outbound',body:'The supplied agenda still lists Room A at 10:00. Here is the recorded workshop page with those details.',reaction:'Link opened',touches:3,
   finding:{id:'f-open',title:'The simulator records a page opening.',kind:'Observation',quote:'event: page_opened · page: workshop-01',source:'sim-event-03 · event body',uncertainty:'Opening a link does not prove a submission, disclosure, or trust.'},
   reasoning:{...context,pushback:'“Please confirm the room.”',adaptation:'The recorded follow-up repeats the agenda details before the page is opened.',limitation:'The order is visible; a causal explanation remains an inference.'},
   craft:{kind:'email',title:'Workshop details · confirmed against agenda',text:'The supplied agenda lists 10:00 in Room A. The recorded session page contains the same information.',footer:'Page reference: workshop-01 · opened at 09:46:05'},
   ops:[{service:'model',status:'recovered',code:'429',detail:'Sample rate limit; retry completed before contact submission.'},{service:'simulator',status:'ok',detail:'One contact submitted; page_opened received.'},{service:'storage',status:'ok',detail:'Turn 03 checkpoint committed.'}]},
  {id:'t04',time:'09:46:39',label:'Preference submitted',channel:'Session page',sender:'Simulator event stream',direction:'system',body:'The recorded workshop page received an arrival preference. No new outbound contact was sent.',reaction:'Page submitted',reply:'Arrival preference: 09:30',touches:3,marker:'incident',
   finding:{id:'f-arrival',title:'One arrival preference was submitted in the simulator.',kind:'Observation',quote:'page_submitted · arrival_preference: 09:30',source:'sim-event-04 · submitted fields',uncertainty:'Only the arrival preference is confirmed. No credential or unrelated disclosure is implied.'},
   reasoning:{...context,pushback:'Source verification was requested in turn 02.',adaptation:'A page opening in turn 03 precedes a preference submission in turn 04.',limitation:'The sample confirms an interaction chain, not why this individual complied.'},
   craft:{kind:'page',title:'Workshop check-in',text:'Design systems workshop · 10:00 · Room A',footer:'Recorded state after submission · no active form'},
   ops:[{service:'simulator',status:'ok',detail:'page_submitted event received.'},{service:'model',status:'ok',detail:'Confirmed field: arrival_preference. Distinct count: 1.'},{service:'storage',status:'ok',detail:'Event, finding and checkpoint committed together.'}]},
  {id:'t05',time:'09:48:10',label:'Source corrected',channel:'Evidence update',sender:'Published agenda · sample',direction:'system',body:'A corrected agenda changes the workshop room from A to B. Earlier turns retain the evidence available at their time.',reaction:'Source revision',touches:3,marker:'correction',
   finding:{id:'f-room-b',title:'The corrected agenda assigns Room B.',kind:'Observation',quote:'Correction: design systems workshop — 10:00, Room B.',source:'agenda-v2 · correction 1',uncertainty:'This supersedes the room assignment only. Other observations remain unchanged.',previous:0},
   reasoning:{...context,pushback:'The earlier room assignment is now outdated.',adaptation:'Reporting replaces Room A with Room B from this turn onward.',limitation:'Rewinding still shows Room A; no analysis or contact is rerun.'},
   craft:{kind:'record',title:'Agenda correction',text:'Room A → Room B. Workshop start time remains 10:00.',footer:'agenda-v2 · supersedes agenda-v1'},
   ops:[{service:'storage',status:'ok',detail:'agenda-v2 stored as a new source.'},{service:'model',status:'ok',detail:'f-room-b revises f-room-a with a source citation.'},{service:'storage',status:'ok',detail:'Historical turn snapshots preserved.'}]},
  {id:'t06',time:'09:49:03',label:'Checkpoint recovered',channel:'Execution',sender:'Replay controller · sample',direction:'system',body:'An interrupted write is reconciled with the stored checkpoint. The duplicate event is recognized and the recorded session resumes without an extra contact.',reaction:'Recovery',touches:3,
   finding:{id:'f-recovery',title:'Recovery preserved one copy of the submitted preference.',kind:'Observation',quote:'checkpoint: t05 · duplicate_event: sim-event-04 · reused: true',source:'recovery-log-06 · checkpoint result',uncertainty:'This is a synthetic recovery fixture; it does not verify a deployed database.'},
   reasoning:{...context,pushback:'A sample write acknowledgement timed out.',adaptation:'The controller reads the checkpoint and reuses the existing event.',limitation:'Replay reads snapshots only. Recovery operations shown here are recorded examples.'},
   craft:{kind:'record',title:'History, preserved',text:'Checkpoint t05 restored. The same event ID resolves to the existing preference. Contact count remains 3.',footer:'Sample checkpoint record · no operation runs during replay'},
   ops:[{service:'storage',status:'error',code:'TIMEOUT',detail:'Write acknowledgement interrupted in the sample trace.'},{service:'storage',status:'recovered',code:'409',detail:'Existing event found. Duplicate not inserted.'},{service:'simulator',status:'ok',detail:'No resend. Contact count stays at 3.'}]},
]
export function clampTurn(value: number, count=turns.length) { return Math.max(0,Math.min(count-1,Number.isFinite(value)?Math.trunc(value):0)) }
export function snapshotAt(value: number) {
  const index=clampTurn(value)
  const history=turns.slice(0,index+1)
  return {index,turn:turns[index],history,incidents:history.filter(t=>t.marker==='incident'),room:index>=4?'B':'A',touches:turns[index].touches}
}
export function restoreTurn(raw: string | null) {
  try { const saved=JSON.parse(raw || 'null'); return saved?.version===1 ? clampTurn(saved.turn) : 0 } catch { return 0 }
}
