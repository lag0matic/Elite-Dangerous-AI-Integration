from src.lib.Event import ConversationEvent, GameEvent, ToolEvent
from src.lib.PromptContext import prompt_build_mode


def test_prompt_build_mode_uses_user_command_for_user_turns():
    events = [
        ConversationEvent(kind="user", content="Request docking."),
    ]

    assert prompt_build_mode(events) == "user_command"


def test_prompt_build_mode_uses_user_command_for_tool_results():
    events = [
        ToolEvent(request=[], results=[]),
    ]

    assert prompt_build_mode(events) == "user_command"


def test_prompt_build_mode_uses_automatic_telemetry_for_game_only_turns():
    events = [
        GameEvent(content={"event": "ProspectedAsteroid", "timestamp": "2026-05-10T00:00:00Z"}, historic=False),
    ]

    assert prompt_build_mode(events) == "automatic_telemetry"
