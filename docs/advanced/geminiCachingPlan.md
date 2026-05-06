# Gemini Explicit Context Caching Plan

## Goal

Add an invisible Gemini-native LLM transport path that preserves the existing
`LLMModel.generate(messages, tools, tool_choice)` interface while using Gemini
explicit context caching for stable prompt and tool content.

The user-facing behavior should not change. Cassia should still receive live
status, game events, chat history, and commander input as normal, and should
still return either text or tool calls in the same shape the rest of the app
expects.

## Cache Rule

Treat the explicit cache as a read-only prompt foundation. Cached content is a
prefix to every request. Never put live game state in the cache.

Cache only:

- Hardcoded system wrapper from `PromptGenerator.generate_prompt`.
- Active character prompt after `{commander_name}` substitution.
- Final resolved tool schemas for the current mode, including built-in tools,
  plugin tools, addon tools, UI tools, web tools, vision tools, and overlay UI
  tools when enabled.

Do not cache:

- Current system, location, fuel, hull, shields, target, station, cargo, missions,
  or any projected status.
- Recent game events.
- Recent chat or Twitch messages.
- Rolling conversation history.
- Tool outputs.
- Latest commander input.

## Desired Runtime Shape

Static cache object:

```python
cache_data = {
    "system_instruction": hardcoded_wrapper + active_character_prompt,
    "tools": resolved_tools_for_active_mode,
    "model": model_name,
}
```

Per-call dynamic request:

```python
dynamic_data = [
    status_snapshot,
    memory_notes,
    recent_events,
    recent_conversation,
    latest_user_or_event,
    tool_results,
]
```

Effective prompt:

```text
[CACHED STATIC PREFIX]
[DYNAMIC REQUEST CONTENT]
```

## Implementation Phases

1. Add Gemini native client dependency, likely `google-genai`, to
   `requirements.txt`.
2. Add a new `GeminiLLMModel` behind the existing `LLMModel.generate` interface.
3. Convert OpenAI-style messages and tools to Gemini-native contents, system
   instruction, tools, function calls, and function responses.
4. Split the first system message plus tools into the static cache foundation.
   Treat all remaining messages as dynamic.
5. Build a canonical cache hash over:
   - cache schema version
   - model name
   - system instruction
   - final resolved tools JSON
6. Persist cache metadata locally:
   - cache hash
   - Gemini cache name/id
   - model name
   - created time
   - expiry/TTL
7. Lazily create or refresh caches:
   - Reuse when hash matches and cache has not expired.
   - Verify a locally remembered cache still exists remotely before reuse.
   - Refresh the TTL when a matching cache is close to expiry.
   - Create a new cache when missing, expired, or hash changed.
   - Let old caches expire naturally unless cleanup is easy.
8. Route `google-ai-studio` Gemini models to `GeminiLLMModel` automatically.
   Keep the existing OpenAI-compatible path as a fallback.
9. Map Gemini usage metadata back into `ModelUsageStats`, including cached
   tokens when available.
10. Add tests for:
   - text-only responses
   - function/tool call conversion, especially `requestDocking`
   - tool result round trips
   - cache reuse when hash matches
   - cache refresh when system prompt or tools change
   - fallback behavior on Gemini cache/API errors

## Notes

- Tool availability changes by mode: `mainship`, `fighter`, `buggy`, and
  `humanoid`. Create caches lazily per final resolved tool set rather than
  prebuilding every possible mode.
- Cache creation uses a 3-hour TTL by default (`10800s`), roughly one normal
  game session. The runtime can reuse a still-live cache after an app restart
  and refresh near-expiry caches so short breaks do not force a rebuild.
- The user spends most time in `mainship`, so main-ship cache reuse is the first
  optimization target.
- Plugin/addon tools must be included by hashing the final `ActionManager`
  resolved tool list, not a hand-maintained list of core tools.
- The existing OpenAI-compatible Gemini path mutates prior tool calls with a
  Google thought signature compatibility field. The Gemini-native path should
  replace that workaround with proper native function call/response formatting.
- The first implementation should prioritize behavior parity and safe fallback
  over maximum caching coverage.
