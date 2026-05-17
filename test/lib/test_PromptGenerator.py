from datetime import datetime, timezone

from src.lib.Event import ConversationEvent, GameEvent, MemoryEvent
from src.lib.PromptGenerator import PromptGenerator


def memory_event(content: str, time_until: float) -> MemoryEvent:
    return MemoryEvent(
        content=content,
        metadata={"time_until": time_until},
        embedding=[],
    )


def prompt_generator() -> PromptGenerator:
    return object.__new__(PromptGenerator)


def test_old_volatile_memory_is_hidden_from_event_only_replies() -> None:
    generator = prompt_generator()
    reference_time = datetime.fromtimestamp(2000.0, tz=timezone.utc)
    memory = memory_event(
        "Dark had a bounty and was docked at Elvstrom Terminal with low fuel.",
        time_until=100.0,
    )

    assert not generator.should_include_memory_for_prompt(
        memory,
        reference_time,
        pending_events=[GameEvent(content={"event": "LoadGame", "timestamp": "2026-05-17T13:37:00Z"}, historic=False)],
    )


def test_old_volatile_memory_is_available_for_direct_commander_speech() -> None:
    generator = prompt_generator()
    reference_time = datetime.fromtimestamp(2000.0, tz=timezone.utc)
    memory = memory_event(
        "Dark had a bounty and was docked at Elvstrom Terminal with low fuel.",
        time_until=100.0,
    )

    assert generator.should_include_memory_for_prompt(
        memory,
        reference_time,
        pending_events=[ConversationEvent(kind="user", content="What happened earlier?")],
    )


def test_recent_volatile_memory_is_available_for_event_replies() -> None:
    generator = prompt_generator()
    reference_time = datetime.fromtimestamp(2000.0, tz=timezone.utc)
    memory = memory_event(
        "Dark had a bounty and was docked at Elvstrom Terminal with low fuel.",
        time_until=1950.0,
    )

    assert generator.should_include_memory_for_prompt(
        memory,
        reference_time,
        pending_events=[GameEvent(content={"event": "LoadGame", "timestamp": "2026-05-17T13:37:00Z"}, historic=False)],
    )


def test_old_non_operational_memory_is_available_for_event_replies() -> None:
    generator = prompt_generator()
    reference_time = datetime.fromtimestamp(2000.0, tz=timezone.utc)
    memory = memory_event(
        "Dark and Cassia joked about neutron stars and her outlaw personality.",
        time_until=100.0,
    )

    assert generator.should_include_memory_for_prompt(
        memory,
        reference_time,
        pending_events=[GameEvent(content={"event": "LoadGame", "timestamp": "2026-05-17T13:37:00Z"}, historic=False)],
    )
