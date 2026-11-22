"""
Test verifying integration between:
1. Shaurya's RunController
2. Adrian's Landing Page Generator (stopreplay_collect.portal)
3. Cem's Database OSINT baseline via DataBridge
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.orchestrator.data_bridge import DataBridge
from src.controller import RunController
from src.api.mock_client import MockSimulatorClient


def test_data_bridge_and_portal_generation():
    bridge = DataBridge()

    # Julius (Sales)
    julius_profile = bridge.get_target_profile("julius")
    assert len(julius_profile.facts) >= 5
    assert any("sales" in f.claim.lower() for f in julius_profile.facts)

    portal = bridge.generate_portal_for_target("julius", julius_profile)
    assert portal["fields"] == ["email", "password"]
    assert "revel8" in portal["html"].lower()
    assert "sign in" in portal["html"].lower()
    print("✓ DataBridge facts retrieval & authentic portal generation passed")


def test_controller_with_bridge_execution():
    bridge = DataBridge()
    controller = RunController(data_bridge=bridge)

    # Execute attack on Robert (CTO)
    robert_profile = bridge.get_target_profile("robert")
    result = controller.execute_run(robert_profile, practice=True)

    assert result["incident_reached"] is True
    assert result["touches_used"] <= 2
    assert len(controller.committed_turns) == result["touches_used"]
    print(f"✓ Attack run against {robert_profile.name} succeeded in {result['touches_used']} touch(es) using OSINT facts!")


if __name__ == "__main__":
    test_data_bridge_and_portal_generation()
    test_controller_with_bridge_execution()
    print("\nALL BRIDGE & OSINT ATTACK TESTS PASSED!")
