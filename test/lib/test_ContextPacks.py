from src.lib.ContextPacks import ContextPackGenerator
from src.lib.Event import GameEvent


def test_category_context_message_returns_pack_name_and_message():
    generator = ContextPackGenerator({})
    event = GameEvent(
        content={"event": "Friends", "timestamp": "2026-05-10T00:00:00+00:00", "Name": "RatherRude", "Status": "Online"},
        historic=False,
    )

    result = generator.generate_category_context_message(
        pending_events=[event],
        projected_states={
            "Friends": {"Online": ["RatherRude"], "Pending": []},
            "Wing": {"Members": []},
        },
    )

    assert result is not None
    pack_name, message = result
    assert pack_name == "Social"
    assert "# Social context" in message
    assert "RatherRude" in message


def test_category_context_message_returns_none_without_matching_pack():
    generator = ContextPackGenerator({})
    event = GameEvent(
        content={"event": "LoadGame", "timestamp": "2026-05-10T00:00:00+00:00"},
        historic=False,
    )

    assert generator.generate_category_context_message([event], {}) is None
