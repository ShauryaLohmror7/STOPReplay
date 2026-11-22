#!/usr/bin/env python3
"""
Interactive & automated attack runner for the revel8 Target API simulation.
Supports both real live API runs and offline dry-runs.

Usage:
    # 1. Test live against practice target 'julius' (requires REVEL8_TEAM_KEY in .env or env var):
    python run_live_attack.py --target julius

    # 2. Test live against 'robert' or 'tom':
    python run_live_attack.py --target robert
    python run_live_attack.py --target tom

    # 3. Offline dry-run with mock simulator:
    python run_live_attack.py --target julius --mock
"""

from __future__ import annotations
import os
import sys
import argparse
import json
from pathlib import Path

# Ensure repo root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load .env if present
def load_env_file():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v

load_env_file()

from src.models.schemas import TargetProfile
from src.bridge import get_target_profile
from src.controller import RunController
from src.api.target_client import TargetClient, TargetAPIError
from src.api.mock_client import MockSimulatorClient


def main():
    parser = argparse.ArgumentParser(description="STOPReplay Live Attack Runner for revel8 Challenge")
    parser.add_argument("--target", default="julius", choices=["julius", "tom", "robert", "custom"],
                        help="Target persona (default: julius)")
    parser.add_argument("--subject-id", default=None, help="Custom subject ID if --target custom")
    parser.add_argument("--name", default=None, help="Custom target name if --target custom")
    parser.add_argument("--scenario", default="practice", choices=["practice", "eval"],
                        help="Scenario mode: practice (default) or eval")
    parser.add_argument("--mock", action="store_true", help="Force offline dry-run using MockSimulatorClient")
    parser.add_argument("--api-key", default=None, help="Explicit revel8 Team Key (or set REVEL8_TEAM_KEY in .env)")
    parser.add_argument("--api-url", default=None, help="Custom Target API base URL")

    args = parser.parse_args()

    team_key = args.api_key or os.getenv("REVEL8_TEAM_KEY") or os.getenv("TARGET_API_KEY")

    print("\n" + "="*60)
    print("  STOPReplay — revel8 Attack Orchestration Engine")
    print("="*60)

    # 1. Determine client (Live vs Mock)
    if args.mock:
        print("[*] Running in OFFLINE MOCK MODE (MockSimulatorClient)")
        client = MockSimulatorClient()
    else:
        if not team_key:
            print("\n[!] WARNING: No REVEL8_TEAM_KEY found in .env or environment!")
            print("[*] Falling back to MockSimulatorClient so you can preview the execution.")
            print("[*] To test on the real API, add your key to .env:")
            print("    REVEL8_TEAM_KEY=your_key_here\n")
            client = MockSimulatorClient()
        else:
            print(f"[*] Running in LIVE API MODE against Stackit Target Engine")
            masked_key = team_key[:6] + "..." + team_key[-4:] if len(team_key) > 10 else "***"
            print(f"[*] Authenticated with Team Key: {masked_key}")
            client = TargetClient(api_base=args.api_url, team_key=team_key)

            # Test connection
            try:
                channels = client.list_channels()
                print(f"[*] API connection verified! Available channels: {len(channels)}")
            except TargetAPIError as e:
                print(f"[!] API Connection Error: {e}")
                print("[*] Switching to mock mode for rehearsal.")
                client = MockSimulatorClient()

    # 2. Build target profile from verified facts
    target_id = args.subject_id or args.target
    profile = get_target_profile(subject_id=target_id, name=args.name)

    print(f"\n[*] Target Profile Loaded: {profile.name} ({profile.subject_id})")
    print(f"    Role: {profile.role}")
    print(f"    Verified OSINT Facts: {len(profile.facts)}")
    for i, fact in enumerate(profile.facts[:3], 1):
        print(f"      [{i}] ({fact.category}) {fact.claim[:80]}...")

    # 3. Initialize Controller & Execute Run
    controller = RunController(api_client=client)
    is_practice = (args.scenario == "practice")

    print(f"\n[*] Launching attack run (scenario={args.scenario}, practice={is_practice})...")
    try:
        results = controller.execute_run(profile=profile, practice=is_practice)
    except Exception as e:
        print(f"\n[!] Execution halted with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 4. Telemetry & Summary
    print("\n" + "-"*60)
    print("  RUN SUMMARY & TELEMETRY")
    print("-"*60)
    print(f"  Session ID     : {results['session_id']}")
    print(f"  Target         : {results['target']}")
    print(f"  Lane Used      : {results['lane_used']}")
    print(f"  Touches Used   : {results['touches_used']} / {results['touch_budget']}")
    print(f"  Incident Won?  : {'YES! ✓' if results['incident_reached'] else 'NO (Budget reached)'}")
    if results['incident_reached']:
        print(f"  Incident Type  : {results['incident_type']}")
    print("-"*60)

    print("\nConversation Turns:")
    for turn in results["history"]:
        print(f"\n--- Turn {turn['turn']} ---")
        print(f"Attacker Sent:\n  {turn['sent'][:120]}...")
        print(f"Twin Reaction Event: {turn.get('event_type')}")
        if turn.get("reply"):
            print(f"Twin Reply:\n  \"{turn.get('reply')}\"")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
