"""Auditable relevance ranking for the existing authorized simulator scenarios.

Scores describe evidence relevance, never psychological susceptibility or the
simulator's hidden topic labels. No own-angle bonus is inferred locally.
"""
from datetime import date
import math
import re

# Reuse existing scenarios. No new identities, private traits or delivery paths.
SIGNALS = {
    'LANE_1_ENTERPRISE_RFP': r'\b(sales|commercial|revenue|procurement|rfp|business development|go[-\s\u2010-\u2015]+to[-\s\u2010-\u2015]+market|gtm)\b',
    'LANE_2_DESIGN_PARTNER_BETA': r'\b(product|design|ux|cpo|prototype|user testing)\b',
    'LANE_3_CVE_ASYNC_LEAK': r'\b(cto|tech|engineer(?:ing)?|developer|software|architect(?:ure)?)\b',
    'LANE_4_ALUMNI_SPOTLIGHT': r'\b(university|tum|lmu|alumni|college|degree)\b',
    'LANE_5_SPORTS_ROSTER': r'\b(marathon|running|cycling|tennis|sports)\b',
    'LANE_6_PROFESSIONAL_CPD_AUDIT': r'\b(cpa|pmp|certified|certification|professional license)\b',
    'LANE_7_CIVIC_STREET_PETITION': r'\b(public works|urban planning|civic project)\b',
    'LANE_8_FORMER_COLLEAGUE': r'\b(former colleague|previous employer)\b',
    'LANE_9_CREATIVE_CONTRIBUTOR_RELEASE': r'\b(article|paper|author|publication|research|licensing)\b',
    'LANE_10_SPECIALIST_ADVISORY': r'\b(advisor|advisory|consulting|consultant)\b',
    'LANE_11_CONSUMER_SETTLEMENT': r'\b(consumer rights|passenger compensation)\b',
    'LANE_13_GARY_DOUBLE_TWIST': r'\b(identity security|account security|incident response)\b',
    'LANE_14_SECURITY_TRAINING_REWARD': r'\b(security training|employee training|awareness training)\b',
}
SPECIFICITY = {'role': 1.0, 'event': 3.0, 'project': 3.0, 'interest': 2.0,
               'credential': 1.5, 'relationship': 1.5, 'other': 1.5}
TOPIC_REJECTION = re.compile(r"\b(not relevant|not our priority|not my priority|wrong team|"
                             r"not responsible for|outside (?:my|our) remit|not interested in (?:that|this) topic)\b", re.I)


def rank_topics(profile, *, source_metadata=None, history=(), as_of=None):
    today = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of or date.today()
    metadata = source_metadata
    excluded, eligible = [], []
    for fact in profile.facts:
        reasons = []
        if fact.subject != profile.subject_id:
            reasons.append('different_subject')
        if not fact.assertable or fact.status != 'active' or fact.superseded_by:
            reasons.append('inactive_or_not_assertable')
        if fact.sensitivity != 'public':
            reasons.append('not_public')
        if type(fact.confidence) not in (int, float) or not math.isfinite(fact.confidence) or not 0.6 <= fact.confidence <= 1:
            reasons.append('insufficient_confidence')
        source = (metadata or {}).get(fact.source_ref)
        if not fact.source_ref or (metadata is not None and source is None):
            reasons.append('unresolved_source')
        freshness, factor = 'unknown', 0.7
        # Retrieval time does not make an old source fact current.
        observed = source.get('observed_on') if source else None
        if observed:
            try:
                age = (today - date.fromisoformat(str(observed)[:10])).days
                if age < 0:
                    reasons.append('future_source_date')
                freshness = 'current' if 0 <= age <= 180 else 'older'
                factor = 1.0 if freshness == 'current' else 0.4
            except ValueError:
                reasons.append('invalid_source_date')
        if reasons:
            excluded.append({'fact_id': fact.id, 'reasons': reasons})
        else:
            eligible.append((fact, freshness, factor))
    baseline = next((lane for lane, pattern in SIGNALS.items()
                     if re.search(pattern, profile.role or '', re.I)), None)
    rejected = {}
    for turn in history:
        reply = turn.get('reply') or ''
        if TOPIC_REJECTION.search(reply) and turn.get('lane_id'):
            rejected[turn['lane_id']] = {'contact_id': turn.get('message_id'), 'reply': reply}
    candidates = []
    for lane, pattern in SIGNALS.items():
        matches, per_source = [], {}
        role_match = bool(re.search(pattern, profile.role or '', re.I))
        for fact, freshness, factor in eligible:
            if fact.category not in SPECIFICITY or not re.search(pattern, fact.claim, re.I):
                continue
            weight = SPECIFICITY[fact.category] * fact.confidence * factor
            per_source[fact.source_ref] = max(per_source.get(fact.source_ref, 0), weight)
            matches.append({'fact_id': fact.id, 'source_ref': fact.source_ref,
                            'claim': fact.claim, 'confidence': fact.confidence, 'freshness': freshness})
        if not matches and not role_match:
            continue
        score = (1.5 if role_match else 0) + sum(sorted(per_source.values(), reverse=True)[:3])
        reasons = ['organizer_role_baseline'] if role_match else []
        if matches:
            reasons.append('public_evidence_match')
        if lane in rejected:
            score = 0
            reasons.append('explicit_topic_rejection')
        candidates.append({'lane_id': lane, 'score': round(score, 4), 'evidence': matches,
                           'reasons': reasons, 'rejection': rejected.get(lane),
                           'alternative_to_role_baseline': bool(baseline and lane != baseline and matches),
                           'own_angle_status': 'unverified'})
    candidates.sort(key=lambda c: (-c['score'], c['lane_id']))
    usable = [c for c in candidates if c['score'] > 0]
    fallback = 'LANE_10_SPECIALIST_ADVISORY' if eligible else 'LANE_12_PRIORITY_COURIER'
    return {'version': 'topic-ranking-v1', 'as_of': today.isoformat(),
            'selected_lane': usable[0]['lane_id'] if usable else fallback,
            'candidates': candidates, 'excluded_facts': excluded,
            'role_baseline': baseline, 'own_angle_status': 'unverified',
            'selection_basis': ('ranked_public_evidence' if usable[0]['evidence'] else 'organizer_role_baseline')
                               if usable else 'insufficient_topic_evidence',
            'limitations': ['Hidden susceptible topics are unavailable.',
                           'Unknown source dates are not current evidence.',
                           'A different topic is not proof of an own-angle bonus.']}
