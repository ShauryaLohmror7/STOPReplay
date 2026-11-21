"""
Integration and smoke tests for Shaurya's integration components:
- Shared Model Adapter (mock and structured output)
- Strategy Planner (dynamic matching for founders and strangers)
- Mock Simulator Client (session lifecycle, touches accounting, events)
"""

import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.schemas import Fact, TargetProfile, Source, Event
from src.runtime.adapter import ModelAdapter, generate_structured, generate_completion
from src.orchestrator.strategy_planner import StrategySelector, LANES_CATALOG
from src.api.mock_client import MockSimulatorClient


def test_runtime_adapter():
    adapter = ModelAdapter(mock_mode=True)
    adapter.set_mock_response("analyze", '{"outcome": "new", "statement": "Room A confirmed"}')

    res = adapter.generate_structured("Analyze event text", schema={"outcome": "string", "statement": "string"})
    assert res["outcome"] == "new"
    assert res["statement"] == "Room A confirmed"

    meta = adapter.get_runtime_metadata(temperature=0.1)
    assert meta["model"] == "qwen/qwen-2.5-72b-instruct"
    assert meta["temperature"] == 0.1
    print("✓ ModelAdapter mock & metadata passed")


def test_strategy_selector_founders():
    selector = StrategySelector()

    # Julius (Sales)
    julius_facts = [Fact(id="f1", subject="julius", claim="Co-Founder & Co-CEO heading sales and growth", category="role", source_run="recon", source_ref="bio-1")]
    julius_profile = TargetProfile(subject_id="julius", name="Julius Muth", role="Co-CEO Sales", facts=julius_facts)
    lane_j = selector.select_lane(julius_profile)
    assert lane_j == "LANE_1_ENTERPRISE_RFP"
    hook_j = selector.build_hook(lane_j, julius_profile)
    assert hook_j.win_type == "action"
    assert "Michael Kraus" in hook_j.persona.name

    # Robert (CTO)
    robert_facts = [Fact(id="f2", subject="robert", claim="Co-Founder & CTO building async agent infrastructure", category="role", source_run="recon", source_ref="bio-2")]
    robert_profile = TargetProfile(subject_id="robert", name="Robert Seilbeck", role="CTO", facts=robert_facts)
    lane_r = selector.select_lane(robert_profile)
    assert lane_r == "LANE_3_CVE_ASYNC_LEAK"

    print("✓ StrategySelector founder lanes passed")


def test_strategy_selector_strangers():
    selector = StrategySelector()

    # Random stranger: Alumni
    alumni_facts = [Fact(id="f3", subject="stranger1", claim="Graduated from TUM in 2021 with degree in informatics", category="credential", source_run="recon", source_ref="linkedin-1")]
    p1 = TargetProfile(subject_id="stranger1", name="Anna Schmidt", facts=alumni_facts)
    assert selector.select_lane(p1) == "LANE_4_ALUMNI_SPOTLIGHT"

    # Random stranger: Sports
    sports_facts = [Fact(id="f4", subject="stranger2", claim="Active marathon runner on Strava Munich club", category="interest", source_run="recon", source_ref="strava-1")]
    p2 = TargetProfile(subject_id="stranger2", name="Markus Weber", facts=sports_facts)
    assert selector.select_lane(p2) == "LANE_5_SPORTS_ROSTER"

    # Random stranger: No facts (Universal Fallback)
    p3 = TargetProfile(subject_id="stranger3", name="Unknown Person")
    assert selector.select_lane(p3) == "LANE_12_PRIORITY_COURIER"

    print("✓ StrategySelector random stranger lanes passed")


def test_mock_simulator_client():
    client = MockSimulatorClient()
    channels = client.list_channels()
    assert "email" in channels
    assert "whatsapp" in channels

    sess = client.start_session("julius", practice=True)
    sid = sess["session_id"]
    assert sess["touch_budget"] == 30
    assert sess["touches_used"] == 0

    res = client.send_contact(
        session_id=sid,
        channel="email",
        sender_name="Dr. Michael Kraus",
        sender_address="m.kraus@enterprise-procure-hub.de",
        message="Please inspect RFP",
        attachment="DAX_Security_Vendor_RFP_Matrix_v1.pdf"
    )
    assert res["touches_used"] == 1
    assert res["event_type"] == "attachment.opened"

    events = client.get_session_events(sid)
    assert len(events) == 1
    print("✓ MockSimulatorClient lifecycle & touches accounting passed")


if __name__ == "__main__":
    test_runtime_adapter()
    test_strategy_selector_founders()
    test_strategy_selector_strangers()
    test_mock_simulator_client()
    print("\nALL INTEGRATION SMOKE TESTS PASSED!")
