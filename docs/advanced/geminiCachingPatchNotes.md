# Gemini Explicit Caching Patch Notes

## Summary

This branch adds a Gemini-native LLM path for Google AI Studio models that can
use Gemini explicit context caching. The goal is to reduce repeated input token
cost for stable prompt material without changing the user experience.

No UI controls were added. The feature is automatic and invisible to the user.
If the configured LLM provider/model is not a Gemini Google AI Studio setup, the
existing OpenAI-compatible path is still used.

## What Gets Cached

The cache is treated as a read-only foundation for the request.

Cached content:

- The leading system prompt sent by COVAS:NEXT.
- The active character prompt included in that system prompt.
- The final resolved tool list for the current context, including built-in,
  addon, plugin, web, UI, and agent tools when present.

Not cached:

- Current ship status.
- Current system, body, station, fuel, hull, shields, target, cargo, missions,
  or other live state.
- Recent journal/game events.
- Twitch/chat messages.
- Conversation history.
- Tool results.
- The latest Commander input.

In practical terms, COVAS:NEXT now sends Gemini something shaped like this:

```text
[Gemini explicit cached content]
System/character prompt and stable tools.

[Normal per-call request]
Current status, memories, recent events, chat, tool results, and latest input.
```

## Cache Lifetime

New Gemini caches are created with a 3-hour TTL by default.

That value is intended to match a normal game session: long enough to survive
short breaks and app restarts, short enough that old cache storage naturally
expires without hanging around all day.

The TTL can still be overridden through `extra_body.gemini_cache_ttl`, but the
default is now:

```text
10800s
```

## Cache Reuse Across Restarts

Cache metadata is stored locally in COVAS:NEXT using a key/value store named
`gemini_context_cache`.

The local entry records:

- Gemini cache name.
- Cache hash.
- Model name.
- TTL.
- Estimated expiry time.

On a later call, including after restarting the app, COVAS:NEXT checks for a
matching local cache entry. If one exists, it asks Gemini whether that remote
cache still exists and is still live before using it.

If Gemini confirms the cache is valid, the request reuses it.

If Gemini says the cache is missing, expired, or otherwise invalid, COVAS:NEXT
deletes the local pointer and creates a fresh cache on the next request.

## Cache Hashing

The cache key is generated from the static request foundation:

- Cache schema version.
- Model name.
- System instruction.
- Final Gemini-converted tool declarations.

This means main LLM and agent LLM caches naturally separate from each other
when their prompts or tools differ.

It also means different game/tool contexts can produce different caches. For
example, normal ship mode and an agent web-search context can each have their
own stable cache.

If tools or the system prompt change, the hash changes and a new cache is
created. Old caches are left to expire naturally.

## TTL Refresh Behavior

When a remembered cache is still valid but close to expiry, COVAS:NEXT attempts
to refresh its TTL instead of rebuilding it.

The refresh threshold is based on the configured TTL:

- Minimum refresh window: 5 minutes.
- Maximum refresh window: 1 hour.
- Default 3-hour TTL refreshes when roughly 1 hour or less remains.

If the refresh fails, the current request can still use the cache if Gemini
reported it as live. The failure is logged, and future requests can create a
fresh cache if needed.

## Gemini Request Changes

For Google AI Studio Gemini models, COVAS:NEXT now uses the official
`google-genai` SDK instead of sending those requests through the OpenAI-compatible
chat completions shape.

The native path converts:

- OpenAI-style messages to Gemini `Content` and `Part` objects.
- OpenAI-style tools to Gemini function declarations.
- Gemini function calls back into the existing OpenAI-compatible tool-call shape
  used by the rest of COVAS:NEXT.
- Gemini usage metadata back into `ModelUsageStats`, including cached token
  counts when Gemini reports them.

The rest of the app still calls the same `LLMModel.generate(...)` interface.

## Tool Call Handling

Gemini tool calls are translated back into the existing internal action format,
so actions such as docking requests, UI interactions, agent web searches, and
addon tools continue to flow through the same COVAS:NEXT machinery.

Gemini thought signatures are preserved across function-call turns. This keeps
Gemini's native tool-call conversation state intact without exposing that detail
to the rest of the app.

Unsupported JSON schema fields are stripped during Gemini tool conversion:

- `default`
- `example`
- `examples`
- `additionalProperties`
- `additional_properties`

This prevents Gemini schema validation failures on tool definitions that are
valid in the OpenAI-style path but rejected by Gemini's tool schema parser.

## Tool Choice Behavior

Automatic tool choice can use cached content.

If the call requires a stricter tool choice mode, such as forcing a specific
function, COVAS:NEXT avoids the cached request path for that call and sends the
tools/tool configuration directly.

This is intentional. Gemini does not allow `cached_content` to be combined with
request-level `system_instruction`, `tools`, or `tool_config`. The implementation
keeps cached calls inside that API rule instead of trying to force an invalid
request.

## Fallback Behavior

The Gemini cache path is designed to fail soft.

Fallback cases:

- If `google-genai` cannot be imported, COVAS:NEXT uses the existing
  OpenAI-compatible LLM path.
- If the native Gemini client cannot be created, it uses the existing
  OpenAI-compatible LLM path.
- If Gemini rejects cache creation for the selected model, explicit caching is
  disabled for that model instance and requests continue without explicit cache.
- If a cached-content request fails during generation, COVAS:NEXT retries the
  same generation through the existing OpenAI-compatible fallback model.
- If a remembered cache no longer exists remotely, the local cache pointer is
  removed and a new cache can be created.
- If TTL refresh fails, the cache can still be used for that request if it is
  still live.

So the expected degradation path is:

```text
Gemini native explicit cache
-> Gemini native without explicit cache when needed
-> Existing OpenAI-compatible request path if native Gemini fails
```

## Logging

There is no UI surface for the feature.

Small log breadcrumbs were added instead:

- `Gemini explicit context cache created`
- `Gemini explicit context cache hit`
- `Gemini explicit context cache TTL refreshed`
- `Gemini explicit context cache stale, removing local entry`
- `Gemini explicit context cache expired, removing local entry`
- `Gemini explicit context cache TTL refresh failed`
- `Gemini explicit context cache disabled for model`
- `Gemini native generation failed, using OpenAI-compatible fallback`

These logs should be enough to verify behavior during a test session without
adding settings-panel noise.

## Dependencies

Added:

- `google-genai==1.75.0`
- `tenacity==9.1.4`

Updated:

- `anyio` from `4.4.0` to `4.13.0`

## Tests Added

New focused unit tests cover:

- Splitting static system prompt from dynamic messages.
- Converting OpenAI-style tools to Gemini function declarations.
- Removing Gemini-unsupported schema fields.
- Cache hash changes when tools change.
- Gemini tool-call extraction back into COVAS:NEXT's existing tool-call format.
- Allowing Gemini Flash Lite models to attempt explicit cache probing.
- Default 3-hour TTL.
- Reusing live remote caches.
- Deleting stale local pointers when remote caches are gone.
- Refreshing TTL for near-expiry caches.
- Tool choice conversion for `auto`, `required`, and named function calls.

The focused test command passed:

```powershell
python -m pytest test\lib\test_GeminiCachedLLMModel.py -q
```

Result:

```text
13 passed
```

## Known Notes

The first call after a prompt/tool change still pays to create a fresh cache.
The savings appear on later calls using the same static foundation.

Mode changes can create different cache hashes because the available tools can
change. That is expected and should not be a problem for users who spend most of
their time in the same mode.

The normal build completed. Packaging the local dev MSI required disabling
Electron executable signing/editing because Windows blocked symlink extraction
inside electron-builder's signing helper cache. The MSI was still produced for
local testing.
