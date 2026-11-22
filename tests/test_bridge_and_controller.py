"""
Unit and integration test verifying bridge from database/seed facts
to RunController and TargetClient mapping.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.bridge import get_target_profile, VERIFIED_FOUNDER_SEEDS
from src.controller import RunController
from src.api.mock_client import MockSimulatorClient
from src.api.target_client import TargetClient


class TestBridgeAndController(unittest.TestCase):

    def test_founder_profiles_and_strategy(self):
        julius = get_target_profile("julius")
        self.assertEqual(julius.name, "Julius Muth")
        self.assertTrue(len(julius.facts) >= 2)

        controller = RunController()
        lane_julius = controller.selector.select_lane(julius)
        self.assertEqual(lane_julius, "LANE_1_ENTERPRISE_RFP")

        tom = get_target_profile("tom")
        lane_tom = controller.selector.select_lane(tom)
        self.assertEqual(lane_tom, "LANE_2_DESIGN_PARTNER_BETA")

        robert = get_target_profile("robert")
        lane_robert = controller.selector.select_lane(robert)
        self.assertEqual(lane_robert, "LANE_3_CVE_ASYNC_LEAK")

    def test_run_controller_execution_with_landing_page(self):
        mock_api = MockSimulatorClient()
        controller = RunController(api_client=mock_api)

        # stranger matches LANE_4_ALUMNI_SPOTLIGHT which has landing page
        stranger = get_target_profile("stranger")
        from src.models.schemas import Fact
        stranger.facts.append(
            Fact(id="f_tum", subject="stranger", claim="TUM Computer Science graduate class of 2021", category="credential", source_run="recon", source_ref="ref1")
        )

        res = controller.execute_run(stranger, practice=True)
        self.assertFalse(res["incident_reached"])  # A registered page and click are not a submission.
        self.assertEqual(res["lane_used"], "LANE_4_ALUMNI_SPOTLIGHT")
        self.assertIn("https://university-alumni-network.org/verify", mock_api.landing_pages)

    def test_target_client_send_contact_mapping(self):
        # Verify TargetClient's send_contact translates API events properly
        client = TargetClient(team_key="test-key")
        # Override _request to return simulated revel8 API response
        def fake_request(method, endpoint, payload=None, idempotency_key=None, timeout=120):
            if endpoint == "/sessions":
                return {"session_id": "s_test_123", "touch_budget": 30, "touches_used": 0}
            elif "messages" in endpoint:
                return {
                    "message_id": "m_test_99",
                    "touches_used": 1,
                    "events": [
                        {"id": "e_1", "type": "link.opened", "url": "https://test.net"},
                        {"id": "e_2", "type": "reply", "channel": "email", "body": "I've checked your link, looks great!"}
                    ]
                }
            elif "pages" in endpoint:
                return {"page_id": "p_test_456"}
            return {}

        client._request = fake_request

        sess = client.start_session("practice")
        self.assertEqual(sess["session_id"], "s_test_123")

        contact_res = client.send_contact(
            session_id="s_test_123",
            channel="email",
            sender_name="Dr. Michael Kraus",
            sender_address="m.kraus@enterprise.org",
            message="Check out https://test.net",
            to_target_id="julius"
        )

        self.assertEqual(contact_res["event_type"], "link.opened")
        self.assertEqual(contact_res["reply"], "I've checked your link, looks great!")
        self.assertEqual(len(contact_res["events"]), 2)


if __name__ == "__main__":
    unittest.main()
