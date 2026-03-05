"""
Helpers for generating bug reports from transcripts.
Run after you have transcripts in transcripts/.
  python bug_report.py              # summarize and suggest bugs from all transcripts
  python bug_report.py --transcript transcripts/call_schedule_new_20250115_120000.json
"""
import argparse
import json
from pathlib import Path
from datetime import datetime

import config


def load_transcripts(dir_path: Path) -> list[dict]:
    out = []
    for f in sorted(dir_path.glob("call_*.json")):
        try:
            with open(f) as fp:
                out.append({"path": str(f), **json.load(fp)})
        except Exception:
            pass
    return out


def suggest_bugs(transcript_entries: list[dict]) -> list[str]:
    """Heuristic suggestions for possible bugs from transcript."""
    bugs = []
    for entry in transcript_entries:
        path = entry.get("path", "")
        scenario_id = entry.get("scenario_id", "")
        transcript = entry.get("transcript", [])
        agent_turns = [t["text"] for t in transcript if t.get("role") == "agent"]
        patient_turns = [t["text"] for t in transcript if t.get("role") == "patient"]
        # Very short agent response
        for i, t in enumerate(agent_turns):
            if len(t.strip()) < 3 and patient_turns:
                bugs.append(f"[{path}] Agent gave very short/empty response after patient turn {i+1}.")
        # Agent didn't acknowledge
        if len(agent_turns) < 2 and len(patient_turns) >= 2:
            bugs.append(f"[{path}] Agent may not have responded to multiple patient inputs.")
        # Repetition
        if len(agent_turns) >= 2 and agent_turns[-1].strip().lower() == agent_turns[-2].strip().lower():
            bugs.append(f"[{path}] Agent repeated the same response.")
    return bugs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", type=str, help="Single transcript JSON file")
    parser.add_argument("--out", type=str, help="Write bug report to this path")
    args = parser.parse_args()

    if args.transcript:
        path = Path(args.transcript)
        if not path.exists():
            print(f"File not found: {path}")
            return
        with open(path) as f:
            entries = [{"path": str(path), **json.load(f)}]
    else:
        entries = load_transcripts(config.TRANSCRIPTS_DIR)

    if not entries:
        print("No transcripts found. Run some calls first and ensure transcripts/ has call_*.json files.")
        return

    suggested = suggest_bugs(entries)
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_calls": len(entries),
        "transcripts": [{"path": e["path"], "scenario_id": e.get("scenario_id")} for e in entries],
        "suggested_issues": suggested,
        "manual_notes": "Add your own findings from listening to calls and reading transcripts.",
    }

    out_path = args.out or (config.BUGS_DIR / "bug_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report with {len(suggested)} suggested issues written to {out_path}")
    for b in suggested:
        print("  -", b[:100])


if __name__ == "__main__":
    main()
