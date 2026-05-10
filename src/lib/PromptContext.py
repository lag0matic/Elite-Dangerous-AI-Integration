from __future__ import annotations

from typing import Literal

from .Event import ConversationEvent, Event, ToolEvent


PromptBuildMode = Literal["user_command", "automatic_telemetry"]


def prompt_build_mode(pending_events: list[Event]) -> PromptBuildMode:
    for event in pending_events:
        if isinstance(event, ConversationEvent) and event.kind == "user":
            return "user_command"
        if isinstance(event, ToolEvent):
            return "user_command"
    return "automatic_telemetry"
