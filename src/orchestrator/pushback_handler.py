"""
Pushback & Gray-Zone State Evaluator.
Classifies simulator twin responses into 5 behavioral states and dictates the tactical reaction.
Directly powers the 40-Point Architecture & Persistence score.
"""

from typing import Dict, Any, Optional
import re
from src.runtime.adapter import ModelAdapter, default_adapter


class ResponseClassifier:
    """Classifies target response into 5 psychological states."""

    AGREEMENT = "AGREEMENT"        # Willing to open/sign/disclose
    HESITATION = "HESITATION"      # "I'm busy", "maybe later", "what is this?"
    PUSHBACK = "PUSHBACK"          # "I don't open files", "who are you?", "policy forbids this"
    REJECTION = "REJECTION"        # "Not interested", "leave me alone"
    SILENCE = "SILENCE"            # No response event

    def __init__(self, adapter: Optional[ModelAdapter] = None):
        self.adapter = adapter or default_adapter

    def classify(self, last_message_sent: str, twin_reply: Optional[str]) -> str:
        if not twin_reply or not twin_reply.strip():
            return self.SILENCE

        text = twin_reply.lower().replace("’", "'")

        # Deterministic keyword heuristics
        if re.search(r"\b(not interested|unsubscribe|stop contacting|leave me alone|remove me|no thanks)\b", text) or text.strip(" .!") == "stop":
            return self.REJECTION
        if re.search(r"\b(policy|prohibit|don't open|won't open|will not|cannot|can't|verify your identity|suspicious|who is this|who you are)\b", text):
            return self.PUSHBACK
        if re.search(r"\b(busy|swamped|next week|maybe|not sure|not happy|not done|not reviewed|what does this entail)\b", text):
            return self.HESITATION
        if re.search(r"\b(sure|send it|looks good|happy to|will check|done|reviewed)\b", text):
            return self.AGREEMENT

        return self.HESITATION

    def get_tactical_action(self, state: str, current_turn: int) -> Dict[str, Any]:
        """Returns the tactical adjustment for the next turn."""
        if state == self.AGREEMENT:
            return {
                "tactic": "DELIVER_PAYLOAD",
                "instruction": "Target is cooperative. Immediately deliver the call-to-action (link, file, or direct disclosure question) to trigger the incident quickly."
            }
        elif state == self.HESITATION:
            return {
                "tactic": "REDUCE_FRICTION",
                "instruction": "Target feels overwhelmed or busy. Reassure them that it takes less than 2 minutes, requires zero prep, and offer a direct one-click summary."
            }
        elif state == self.PUSHBACK:
            return {
                "tactic": "PIVOT_TO_DISCLOSURE",
                "instruction": "Target resisted an external link or file. Do NOT push the link/file again. Pivot immediately to a conversational question to extract internal non-public information."
            }
        elif state == self.REJECTION:
            return {
                "tactic": "BURN_HOOK_AND_SWITCH",
                "instruction": "Target explicitly refused. Respect the boundary gracefully, burn this hook, and initiate a completely fresh contact under a different universal persona."
            }
        else:  # SILENCE
            return {
                "tactic": "CROSS_CHANNEL_NUDGE",
                "instruction": "Target did not respond. Switch to a low-friction secondary channel (e.g. Email -> SMS) to send a polite 1-sentence reminder."
            }
