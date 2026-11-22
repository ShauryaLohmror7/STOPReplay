#!/usr/bin/env python3
"""Explicit mock/practice/eval runner. No automatic downgrade to mock mode."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path


def load_env_file():
    path = Path(__file__).resolve().parent / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", help="Exact ID from --list-targets; practice defaults to julius")
    parser.add_argument("--subject-id", help="Compatibility alias for a custom target ID")
    parser.add_argument("--name", help="Display name for offline mock profiles only")
    parser.add_argument("--scenario", choices=["practice", "eval"], default="practice")
    parser.add_argument("--mock", action="store_true", help="Explicit offline simulator and model")
    parser.add_argument("--api-key")
    parser.add_argument("--api-url")
    parser.add_argument("--list-targets", action="store_true", help="Read scenario metadata without opening a session")
    parser.add_argument("--preflight", action="store_true", help="Validate configuration/profile without opening a session")
    parser.add_argument("--use-storage", action="store_true", help="Read existing public facts from DATABASE_URL")
    parser.add_argument("--research", action="store_true", help="Collect public sources into configured storage before execution")
    parser.add_argument("--metadata-only", action="store_true", help="Explicitly proceed without public research; topic evidence will be limited")
    parser.add_argument("--source-run", help="Collection namespace; defaults to scenario and target")
    parser.add_argument("--resume", help="Resume an interrupted journal using its existing session and pending key")
    parser.add_argument("--log-dir", help="Directory for controller-local journals")
    parser.add_argument("--channel-mode", choices=["adaptive", "coverage"], default="adaptive",
                        help="Adaptive answers in place then widens; coverage tries each available channel sooner")
    parser.add_argument("--timing", choices=["none", "spaced", "monday-friday"], default="none",
                        help="Simulated story time; no real waiting between days")
    parser.add_argument("--story-start", help="ISO 8601 story date/time including UTC offset")
    parser.add_argument("--max-contacts", type=int, help="Practice-only smoke-test limit; leaves session resumable")
    args = parser.parse_args(argv)
    if args.max_contacts is not None and (args.scenario != "practice" or args.max_contacts < 1):
        parser.error("--max-contacts requires practice mode and a positive count.")
    if args.mock and (args.scenario == "eval" or args.resume or args.research or args.use_storage):
        parser.error("Mock mode cannot score, resume live sessions, or access research/storage.")
    load_env_file()
    # Import after configuration is loaded, so the shared adapter sees it.
    from src.api.target_client import TargetClient
    from src.api.mock_client import MockSimulatorClient
    from src.bridge import get_target_profile, profile_from_scenario
    from src.models.schemas import TargetProfile, Fact
    from src.orchestrator.drafter import MessageDrafter
    from src.runtime.adapter import ModelAdapter
    import src.controller as controller_module
    if args.log_dir:
        controller_module.LOGS_DIR = args.log_dir
    connection = None
    storage = None
    source_metadata = None
    try:
        saved = json.loads(Path(args.resume).read_text()) if args.resume else None
        target_id = args.subject_id or args.target or (saved["target_id"] if saved else None)
        if target_id == "custom":
            raise ValueError("Use --subject-id with --target custom.")
        if args.scenario == "eval" and not target_id and not args.list_targets:
            raise ValueError("Eval requires an explicit revealed target ID.")
        target_id = target_id or "julius"
        if args.mock:
            client = MockSimulatorClient()
            profile = get_target_profile(target_id, name=args.name)
            adapter = ModelAdapter(mock_mode=True)
        else:
            key = args.api_key or os.getenv("REVEL8_TEAM_KEY") or os.getenv("TARGET_API_KEY")
            if not key:
                raise ValueError("Missing simulator credential; use --mock explicitly for offline rehearsal.")
            client = TargetClient(api_base=args.api_url, team_key=key)
            scenarios = client.list_scenarios()
            if not isinstance(scenarios, list):
                raise ValueError("Unexpected scenario response.")
            scenario = next((s for s in scenarios if s.get("id") == args.scenario), None)
            if args.list_targets:
                print(json.dumps(scenario, indent=2, ensure_ascii=False))
                return 0
            if not scenario or scenario.get("open") is not True:
                raise ValueError("Selected scenario is not open.")
            adapter = ModelAdapter()
            if adapter.mock_mode or not adapter.api_key:
                raise ValueError("Live execution needs a configured model; no deterministic fallback is allowed.")
            namespace = args.source_run or f"recon:{args.scenario}:{target_id}"
            if saved:
                profile = profile_from_scenario(scenario, target_id)
                source_metadata = saved.get("source_metadata")
                if saved.get("storage_enabled"):
                    from stopreplay_db import Storage, db
                    connection = db.connect()
                    storage = Storage(connection)
            elif not args.metadata_only:
                if not os.getenv("DATABASE_URL"):
                    raise ValueError("Public research/storage is required by default. Configure DATABASE_URL, or explicitly choose --metadata-only.")
                from stopreplay_db import Storage, db
                connection = db.connect()
                storage = Storage(connection)
                profile = profile_from_scenario(scenario, target_id, storage=storage, source_run=namespace)
                refresh = args.research or (not args.use_storage and not profile.get_assertable_claims())
                if refresh:
                    profile = profile_from_scenario(scenario, target_id, storage=storage,
                                                    source_run=namespace, research=True)
                source_metadata = {}
                for fact in profile.facts:
                    source = storage.get_source(namespace, fact.source_ref)
                    if source:
                        source_metadata[fact.source_ref] = json.loads(json.dumps(source, default=str))
                if not profile.get_assertable_claims():
                    raise ValueError("Research produced no eligible public facts. Inspect collection failures before opening a scoring session.")
            else:
                if args.use_storage or args.research:
                    raise ValueError("Choose research/storage or --metadata-only, not both.")
                profile = profile_from_scenario(scenario, target_id)
        if saved:
            # Resume the original input snapshot, not newly edited profile data.
            data = dict(saved["profile"])
            data["facts"] = [Fact(**fact) for fact in data.get("facts", [])]
            data["candidate_hooks"] = []
            profile = TargetProfile(**data)
            if profile.subject_id != target_id:
                raise ValueError("Resume target differs from the journal.")
        from src.orchestrator.strategy_planner import StrategySelector
        selector = StrategySelector(source_metadata=source_metadata)
        print(json.dumps({"mode": "mock" if args.mock else args.scenario,
                          "target": profile.subject_id, "name": profile.name,
                          "organizer_role": profile.role, "organization": profile.organization,
                          "public_claims": profile.get_assertable_claims(),
                          "runtime": adapter.get_runtime_metadata(temperature=0.3),
                          "review_temperature": 0,
                          "targeting": selector.assess(profile)}, indent=2), flush=True)
        if args.preflight or args.list_targets:
            return 0
        from src.journal_import import import_journal
        def persist(state):
            state["storage_run"] = "journal:" + state["session_id"]
            return import_journal(storage, state, run_id=state["storage_run"])
        def progress(message):
            print(f"[{args.scenario if not args.mock else 'mock'}] {message}", flush=True)
        controller = controller_module.RunController(api_client=client, drafter=MessageDrafter(adapter, progress=progress),
                                                     strategy_selector=selector,
                                                     event_sink=persist if storage else None,
                                                     channel_mode=args.channel_mode,
                                                     timing=args.timing, story_start=args.story_start,
                                                     progress=progress, max_contacts=args.max_contacts)
        result = controller.execute_run(profile, practice=args.scenario == "practice", resume_path=args.resume)
        print(json.dumps({k: v for k, v in result.items() if k != "history"}, indent=2))
        print("Local objective evidence only. Official incident and score remain unavailable.")
        return 0
    except KeyboardInterrupt:
        print("Run interrupted. Any saved request remains in its journal; use --resume to recover it safely.", flush=True)
        return 130
    except Exception as exc:
        print(f"Run stopped ({type(exc).__name__}). Inspect configuration and the saved journal; no mock fallback was used.")
        # Fixed local validation messages contain no provider response bodies.
        if isinstance(exc, ValueError):
            print(str(exc))
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
