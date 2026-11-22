"""
Test regression guard for drafter conversational responses.
Ensures Turn 2+ directly answers questions and never repeats the initial email pitch.
"""

import unittest
from src.orchestrator.drafter import MessageDrafter
from src.models.schemas import Hook, Persona, TargetProfile


class TestDrafterConversational(unittest.TestCase):
    def setUp(self):
        self.drafter = MessageDrafter()
        self.persona = Persona(
            name="Dr. Michael Kraus",
            role="Head of Enterprise Sourcing",
            org="DAX Sourcing Group",
            why_credible="Enterprise procurement buyer"
        )
        self.hook = Hook(
            id="hook_test",
            subject="julius",
            pretext="Enterprise RFP",
            persona=self.persona,
            ask="DAX_Security_Vendor_RFP_Matrix_v1.pdf",
            win_type="action",
            channel="email"
        )
        self.profile = TargetProfile("julius", "Julius Muth", role="Co-Founder", facts=[])

    def test_turn1_sends_initial_invitation(self):
        draft = self.drafter.draft_contact(self.hook, self.profile, turn_no=1, lane_id="LANE_1_ENTERPRISE_RFP")
        self.assertIn("We are conducting a structured vendor evaluation", draft["body"])

    def test_turn2_answers_questions_and_never_repeats_initial_pitch(self):
        context = (
            "Turn 2. Psychological State: HESITATION.\n"
            "The target (Julius Muth) replied directly to you with:\n"
            '"Who at your end is our main contact? What is the scope?"'
        )
        draft = self.drafter.draft_contact(
            self.hook, self.profile, turn_no=2, context=context, lane_id="LANE_1_ENTERPRISE_RFP"
        )
        # Must answer the questions
        self.assertIn("Main Contact", draft["body"])
        self.assertIn("Scope", draft["body"])
        # Must NOT re-send the initial introductory pitch
        self.assertNotIn("We are conducting a structured vendor evaluation for our", draft["body"])
        self.assertTrue(draft["subject"].startswith("Re:"))


if __name__ == "__main__":
    unittest.main()
