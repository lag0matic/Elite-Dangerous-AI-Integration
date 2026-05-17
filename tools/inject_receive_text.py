from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_JOURNAL_DIR = (
    Path.home()
    / "Saved Games"
    / "Frontier Developments"
    / "Elite Dangerous"
)


def latest_journal(journal_dir: Path) -> Path:
    journals = [
        path
        for path in journal_dir.iterdir()
        if path.is_file() and path.name.startswith("Journal.") and path.suffix == ".log"
    ]
    if not journals:
        raise FileNotFoundError(f"No Journal.*.log files found in {journal_dir}")
    return max(journals, key=lambda path: path.stat().st_mtime)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append a synthetic Elite journal ReceiveText event for COVAS dev testing."
    )
    parser.add_argument("--journal-dir", type=Path, default=DEFAULT_JOURNAL_DIR)
    parser.add_argument("--from-name", default="Mara Voss")
    parser.add_argument("--message", default="I'm gonna boil you up.")
    parser.add_argument("--channel", default="npc")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    journal_path = latest_journal(args.journal_dir)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    event = {
        "timestamp": timestamp,
        "event": "ReceiveText",
        "From": args.from_name,
        "From_Localised": args.from_name,
        "Message": args.message,
        "Message_Localised": args.message,
        "Channel": args.channel,
    }
    line = json.dumps(event, ensure_ascii=False)

    if args.dry_run:
        print(journal_path)
        print(line)
        return

    with journal_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")

    print(f"Injected ReceiveText into {journal_path}")
    print(line)


if __name__ == "__main__":
    main()
