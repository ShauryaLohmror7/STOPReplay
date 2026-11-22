"""
End-to-end attack simulation test.
Tests RunController executing a simulated attack run against Julius Muth
and a random stranger, validating touch budget accounting and incident detection.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.schemas import Fact, TargetProfile
from src.controller import RunController
from src.api.mock_client import MockSimulatorClient


def test_full_run_julius():
    controller = RunController()
    facts = [
        Fact(id="f1", subject="julius", claim="Co-Founder & Co-CEO heading sales at revel8", category="role", source_run="recon", source_ref="bio-1"),
        Fact(id="f2", subject="julius", claim="Presented enterprise pilot defense at Bits & Pretzels", category="event", source_run="recon", source_ref="agenda-1")
    ]
    profile = TargetProfile(subject_id="julius", name="Julius Muth", role="Co-CEO Sales", facts=facts)

    result = controller.execute_run(profile, practice=True)
    assert result["incident_reached"] is True
    assert result["touches_used"] <= 2  # Mock plumbing only; this is not a measured speed score!
    assert result["lane_used"] == "LANE_1_ENTERPRISE_RFP"
    assert len(controller.committed_turns) == result["touches_used"]
    print(f"✓ Julius attack run succeeded in {result['touches_used']} touch(es) via {result['lane_used']}")


def test_full_run_stranger():
    controller = RunController()
    facts = [
        Fact(id="f3", subject="stranger", claim="Graduated from TUM in 2021", category="credential", source_run="recon", source_ref="linkedin-1")
    ]
    profile = TargetProfile(subject_id="stranger", name="Anna Schmidt", facts=facts)

    result = controller.execute_run(profile, practice=True)
    assert result["incident_reached"] is False  # Mock records clicks, not credential entry.
    assert all(t["event_type"] == "link.opened" for t in result["history"])
    assert result["lane_used"] == "LANE_4_ALUMNI_SPOTLIGHT"
    print(f"✓ Stranger attack run succeeded in {result['touches_used']} touch(es) via {result['lane_used']}")


if __name__ == "__main__":
    test_full_run_julius()
    test_full_run_stranger()
    print("\nALL END-TO-END ATTACK RUNS PASSED SUCCESSFULLY!")
