from pathlib import Path
import re

from src.lib.Event import GameEvent, ProjectedEvent, StatusEvent
from src.lib.EventCategories import (
    GAME_EVENT_CATEGORIES,
    categories_for_events,
    event_category,
    event_name_to_category,
)


def _parse_ui_event_categories() -> dict[str, tuple[str, ...]]:
    source = Path("ui/src/app/components/character-settings/game-event-categories.ts").read_text()
    categories: dict[str, list[str]] = {}
    current_category: str | None = None

    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        category_match = re.match(r"""["']([^"']+)["']:\s*\[""", line)
        if category_match:
            current_category = category_match.group(1)
            categories[current_category] = []
            continue

        if current_category and line.startswith("]"):
            current_category = None
            continue

        if current_category:
            event_match = re.match(r"""["']([^"']+)["']\s*,?""", line)
            if event_match:
                categories[current_category].append(event_match.group(1))

    return {category: tuple(events) for category, events in categories.items()}


def test_backend_event_categories_match_ui_reaction_categories():
    assert GAME_EVENT_CATEGORIES == _parse_ui_event_categories()


def test_event_name_to_category_maps_known_events_case_insensitively():
    assert event_name_to_category("ProspectedAsteroid") == "Mining"
    assert event_name_to_category("prospectedasteroid") == "Mining"
    assert event_name_to_category("FSDJump") == "Ship Updates"
    assert event_name_to_category("Friends") == "Social"
    assert event_name_to_category("MissionAccepted") == "Missions & Quests"
    assert event_name_to_category("NotARealEvent") is None
    assert event_name_to_category(None) is None


def test_event_category_reads_supported_event_wrappers():
    game_event = GameEvent(content={"event": "MarketSell", "timestamp": "2026-05-10T00:00:00Z"}, historic=False)
    status_event = StatusEvent(status={"event": "LandingGearDown"})
    projected_event = ProjectedEvent(content={"event": "CombatEntered"})

    assert event_category(game_event) == "Trading"
    assert event_category(status_event) == "Ship Updates"
    assert event_category(projected_event) == "Combat"


def test_categories_for_events_groups_events_by_ui_category():
    mining_event = GameEvent(content={"event": "ProspectedAsteroid", "timestamp": "2026-05-10T00:00:00Z"}, historic=False)
    social_event = ProjectedEvent(content={"event": "Friends"})
    unknown_event = StatusEvent(status={"event": "SomethingElse"})

    grouped = categories_for_events([mining_event, social_event, unknown_event])

    assert grouped == {
        "Mining": [mining_event],
        "Social": [social_event],
    }
