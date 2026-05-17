from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lib.Event import (  # noqa: E402
    ConversationEvent,
    Event,
    EventClasses,
    GameEvent,
    MemoryEvent,
    ProjectedEvent,
    StatusEvent,
)
from lib.FocusProfiles import event_name, resolve_focus_profile, should_include_event  # noqa: E402
import lib.PromptGenerator as prompt_generator_module  # noqa: E402
from lib.PromptGenerator import PromptGenerator  # noqa: E402
from lib.SystemDatabase import SystemDatabase  # noqa: E402


DEFAULT_APPDATA = Path.home() / "AppData" / "Roaming" / "com.covas-next.ui"
DEFAULT_DB = DEFAULT_APPDATA / "covas.db"
DEFAULT_CONFIG = DEFAULT_APPDATA / "config.json"

COMBAT_TRIGGER_EVENTS = {
    "UnderAttack",
    "CombatEntered",
    "Bounty",
    "BountyScanned",
    "FactionKillBond",
    "ShipTargeted",
    "ShieldState",
    "HullDamage",
    "HeatWarning",
    "HeatDamage",
    "Died",
    "CockpitBreached",
    "BeingInterdicted",
    "Interdicted",
}

MINING_TRIGGER_EVENTS = {
    "ProspectedAsteroid",
    "MiningRefined",
    "LaunchDrone",
    "EjectCargo",
    "CollectCargo",
    "CargoScoopDeployed",
    "CargoScoopRetracted",
    "ReservoirReplenished",
    "RememberLimpets",
}

TRAVEL_TRIGGER_EVENTS = {
    "ApproachBody",
    "ApproachSettlement",
    "CarrierJump",
    "CodexEntry",
    "DiscoveryScan",
    "Docked",
    "DockingCancelled",
    "DockingDenied",
    "DockingGranted",
    "DockingRequested",
    "DockingTimeout",
    "FSDJump",
    "FSDTarget",
    "FSSAllBodiesFound",
    "FSSBodySignals",
    "FSSDiscoveryScan",
    "FSSSignalDiscovered",
    "FuelScoop",
    "HighGravityWarning",
    "HighValueLandmarksBody",
    "HGECandidateFound",
    "JetConeBoost",
    "Location",
    "NavBeaconScan",
    "NavRoute",
    "NavRouteClear",
    "SAAScanComplete",
    "SAASignalsFound",
    "Scan",
    "StartJump",
    "SupercruiseDestinationDrop",
    "SupercruiseEntry",
    "SupercruiseExit",
    "Undocked",
}


@dataclass
class StoredEvent:
    id: int
    cls: str
    data: dict[str, Any]
    processed_at: float | None
    responded_at: float | None


def event_summary(event: Event) -> str:
    name = event_name(event)
    content: Any
    if isinstance(event, (GameEvent, ProjectedEvent)):
        content = event.content
    elif isinstance(event, StatusEvent):
        content = event.status
    elif isinstance(event, ConversationEvent):
        text = event.content.replace("\n", " ")
        return f"{event.kind}: {text[:120]}"
    elif isinstance(event, MemoryEvent):
        return f"memory: {event.content[:120]}"
    else:
        return name

    if not isinstance(content, dict):
        return name

    details: list[str] = []
    for key in (
        "PilotName_Localised",
        "PilotName",
        "Ship_Localised",
        "Target_Localised",
        "LegalStatus",
        "Bounty",
        "TotalReward",
        "Message",
        "Channel",
        "From",
    ):
        value = content.get(key)
        if value not in (None, "", []):
            details.append(f"{key}={value}")

    return name if not details else f"{name}: " + ", ".join(details[:5])


def instantiate_event(row: StoredEvent) -> Event | None:
    for cls in EventClasses:
        if cls.__name__ == row.cls:
            try:
                event = cls(**row.data)
                event.processed_at = row.processed_at or 0.0
                event.responded_at = row.responded_at
                return event
            except TypeError as exc:
                print(f"Skipping row {row.id}: could not build {row.cls}: {exc}")
                return None
    return None


def load_config(config_path: Path) -> tuple[str, str, str, list[str], list[str]]:
    if not config_path.exists():
        return ("Dark", "Unknown", "Cassia prompt for {commander_name}", [], [])

    config = json.loads(config_path.read_text(encoding="utf-8"))
    commander_name = str(config.get("commander_name") or "Dark")
    characters = config.get("characters") or []
    active_index = int(config.get("active_character_index") or 0)
    character = characters[active_index] if 0 <= active_index < len(characters) else {}
    character_name = str(character.get("name") or "Unknown")
    character_prompt = str(character.get("character") or "Cassia prompt for {commander_name}")
    reactions = character.get("event_reactions") or {}

    important_game_events = [
        str(name)
        for name, state in reactions.items()
        if state == "on"
    ]
    disabled_game_events = [
        str(name)
        for name, state in reactions.items()
        if state == "hidden"
    ]
    return (commander_name, character_name, character_prompt, important_game_events, disabled_game_events)


def open_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_stored(row: sqlite3.Row) -> StoredEvent:
    return StoredEvent(
        id=int(row["id"]),
        cls=str(row["class"]),
        data=json.loads(str(row["data"])),
        processed_at=float(row["processed_at"]) if row["processed_at"] is not None else None,
        responded_at=float(row["responded_at"]) if row["responded_at"] is not None else None,
    )


def find_latest_trigger(conn: sqlite3.Connection) -> StoredEvent:
    trigger_events = COMBAT_TRIGGER_EVENTS | MINING_TRIGGER_EVENTS | TRAVEL_TRIGGER_EVENTS
    clauses = [
        "data LIKE ?"
        for _ in trigger_events
    ]
    params = [f'%"event": "{name}"%' for name in trigger_events]
    sql = f"""
        SELECT id, class, data, processed_at, responded_at
        FROM events_v1
        WHERE {" OR ".join(clauses)}
        ORDER BY id DESC
        LIMIT 1
    """
    row = conn.execute(sql, params).fetchone()
    if not row:
        raise SystemExit("No combat trigger events found.")
    return row_to_stored(row)


def load_stored_by_id(conn: sqlite3.Connection, row_id: int) -> StoredEvent:
    row = conn.execute(
        """
        SELECT id, class, data, processed_at, responded_at
        FROM events_v1
        WHERE id = ?
        """,
        (row_id,),
    ).fetchone()
    if not row:
        raise SystemExit(f"No event row found for id {row_id}.")
    return row_to_stored(row)


def load_event_window(
    conn: sqlite3.Connection,
    end_id: int,
    limit: int,
) -> list[StoredEvent]:
    rows = conn.execute(
        """
        SELECT id, class, data, processed_at, responded_at
        FROM events_v1
        WHERE id <= ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (end_id, limit),
    ).fetchall()
    return [row_to_stored(row) for row in rows][::-1]


def load_pending_group(conn: sqlite3.Connection, responded_at: float | None) -> list[StoredEvent]:
    if responded_at in (None, 0.0):
        return []

    rows = conn.execute(
        """
        SELECT id, class, data, processed_at, responded_at
        FROM events_v1
        WHERE responded_at = ?
        ORDER BY id ASC
        """,
        (responded_at,),
    ).fetchall()
    return [row_to_stored(row) for row in rows]


def build_projected_states(events: list[Event]) -> dict[str, dict[str, Any]]:
    status: dict[str, Any] = {}
    target: dict[str, Any] = {}
    in_combat = False

    for event in events:
        name = event_name(event)
        if isinstance(event, StatusEvent) and event.status.get("event") == "Status":
            status = dict(event.status)
        elif isinstance(event, (GameEvent, ProjectedEvent)) and name == "ShipTargeted":
            content = dict(event.content)
            if content.get("TargetLocked", True):
                target = content
        elif name == "CombatEntered":
            in_combat = True
        elif name == "CombatExited":
            in_combat = False

    if any(event_name(event) in {"UnderAttack", "Bounty", "BountyScanned"} for event in events[-20:]):
        in_combat = True

    return {
        "CurrentStatus": status,
        "Target": target,
        "InCombat": {"InCombat": in_combat},
    }


def contains_any(text: str, needles: list[str]) -> list[str]:
    lower = text.lower()
    return [needle for needle in needles if needle.lower() in lower]


def raw_journal_tokens(text: str) -> list[str]:
    return sorted(set(re.findall(r"\$[^\s\"',{}[\]]+?;", text)))


def print_prompt_messages(prompt: list[dict[str, str]], max_chars: int) -> None:
    print("\n--- Filtered Prompt Messages ---")
    for index, message in enumerate(prompt):
        content = message.get("content", "")
        content = content if len(content) <= max_chars else content[:max_chars] + "\n...[truncated]"
        print(f"\n[{index}] {message.get('role')}")
        print(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a COVAS DB event window through the focus-profile prompt filter.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--around-id", type=int, default=None, help="Replay around a specific events_v1 row id.")
    parser.add_argument("--limit", type=int, default=150, help="Number of prior events to load.")
    parser.add_argument("--max-message-chars", type=int, default=1200)
    parser.add_argument("--single-pending", action="store_true", help="Treat only --around-id as pending instead of loading its full responded_at group.")
    parser.add_argument("--show-prompt", action="store_true")
    args = parser.parse_args()

    conn = open_db(args.db)
    target = load_stored_by_id(conn, args.around_id) if args.around_id else find_latest_trigger(conn)
    pending_rows = [target] if args.single_pending else load_pending_group(conn, target.responded_at)
    end_id = max([target.id, *[row.id for row in pending_rows]]) if pending_rows else target.id
    stored_window = load_event_window(conn, end_id, args.limit)
    stored_by_id = {row.id: row for row in stored_window}
    for row in pending_rows:
        stored_by_id[row.id] = row
    stored_window = [stored_by_id[row_id] for row_id in sorted(stored_by_id)]

    events = [event for row in stored_window if (event := instantiate_event(row))]
    pending_ids = {row.id for row in pending_rows} or {target.id}
    pending_events = [
        event
        for row, event in zip(stored_window, events)
        if row.id in pending_ids
    ]
    projected_states = build_projected_states(events)

    focus = resolve_focus_profile(projected_states, pending_events)
    kept: list[str] = []
    filtered: dict[str, int] = {}
    included_event_counts: dict[str, int] = {}
    for row, event in zip(stored_window, events):
        name = event_name(event)
        if not should_include_event(event, focus, row.id in pending_ids):
            filtered[name] = filtered.get(name, 0) + 1
            continue

        max_events = focus.profile.max_events_per_name.get(name)
        if max_events is not None and included_event_counts.get(name, 0) >= max_events:
            filtered[name] = filtered.get(name, 0) + 1
            continue

        included_event_counts[name] = included_event_counts.get(name, 0) + 1
        kept.append(name)

    commander_name, character_name, character_prompt, important_events, disabled_events = load_config(args.config)
    generator = PromptGenerator(
        commander_name=commander_name,
        character_prompt=character_prompt,
        important_game_events=important_events,
        disabled_game_events=disabled_events,
        system_db=SystemDatabase(),
    )
    prompt_generator_module.log = lambda *args, **kwargs: None
    logging.disable(logging.CRITICAL)
    prompt, stats = generator.generate_prompt(events, projected_states, pending_events, [])
    joined_prompt = "\n".join(message.get("content", "") for message in prompt)
    user_visible_prompt = "\n".join(
        message.get("content", "")
        for message in prompt
        if (
            message.get("role") != "system"
            and not message.get("content", "").startswith("Focus profile:")
        )
    )

    print("Replay target")
    print(f"  db: {args.db}")
    print(f"  target row: {target.id} ({target.cls}) responded_at={target.responded_at}")
    print(f"  end row: {end_id}")
    print(f"  loaded events: {len(events)}")
    print(f"  pending events: {len(pending_events)}")
    print(f"  commander: {commander_name}")
    print(f"  active character: {character_name}")

    print("\nEffective focus")
    print(f"  profile: {focus.profile.name}")
    print(f"  reason: {focus.reason}")
    print(f"  automatic: {focus.automatic}")
    print(f"  prompt messages: {len(prompt)}")
    print(f"  prompt chars: {len(joined_prompt)}")
    print(f"  stats: system={stats.system_chars} status={stats.status_chars} conversation={stats.conversation_chars} memory={stats.memory_chars}")

    print("\nPending group")
    for row in pending_rows or [target]:
        event = instantiate_event(row)
        print(f"  {row.id}: {row.cls} {event_summary(event) if event else row.cls}")

    print("\nKept event names")
    kept_counts: dict[str, int] = {}
    for name in kept:
        kept_counts[name] = kept_counts.get(name, 0) + 1
    for name, count in sorted(kept_counts.items()):
        print(f"  {name}: {count}")

    print("\nFiltered event names")
    for name, count in sorted(filtered.items()):
        print(f"  {name}: {count}")

    print("\nNoise checks")
    for label, needles in {
        "chat/economy/social": ["Twitch", "trade", "selling", "Star Citizen", "community goal", "fleet carrier"],
        "memory/logbook wrappers": ["Ship logbook", "memory:"],
        "old assistant voice": ["What else matters", "What a bunch"],
    }.items():
        hits = contains_any(user_visible_prompt, needles)
        print(f"  {label}: {'FOUND ' + ', '.join(hits) if hits else 'clear'}")

    raw_tokens = raw_journal_tokens(user_visible_prompt)
    print(f"  raw journal tokens: {'FOUND ' + ', '.join(raw_tokens[:20]) if raw_tokens else 'clear'}")

    if args.show_prompt:
        print_prompt_messages(prompt, args.max_message_chars)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
