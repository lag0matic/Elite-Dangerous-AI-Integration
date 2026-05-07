# Context Trim Test Notes

This branch is a cost and latency experiment layered on top of the Gemini
explicit caching work. The goal is to reduce uncached per-call prompt size
without changing the user's character prompt, breaking Gemini cache behavior, or
removing live game awareness that Cassia needs for ordinary play.

## Main Changes

### Routine Status Trimming

`PromptGenerator.generate_status_message()` now supports a `detail` mode:

- `full`: the existing broad status payload, kept as the default for existing
  callers.
- `core`: a smaller routine assistant status payload used for ordinary
  conversation and telemetry reactions.

Core status keeps live operational context such as:

- active vehicle mode and current ship status
- ship identity, cargo total, fuel, jump range, landing pad size
- current location, docked/station state, local system summary
- current target and danger-related state when present
- plugin status generators

Core status omits heavier catalog-style sections unless full detail is needed:

- local station lists
- local body lists
- faction and power lists
- community goals
- nav route details
- fleet carrier lists
- active quest catalog entries
- colonisation construction details
- friends list
- available engineer list
- full loadout/module detail

The assistant prompt path chooses `full` status when the latest user message or
pending game event asks for broader catalog information, such as stations,
bodies, route, cargo, modules, engineers, missions, carriers, materials, or
inventory. Otherwise it uses `core`.

### Voice Guardrail

The shared assistant system prompt now includes a small style correction:

- prefer `we` for shared ship-state phrasing when it does not imply Cassia
  personally performed a ship action
- avoid overusing `the ship` unless a detached technical tone is appropriate

This was added after the trim caused Cassia to over-correct toward phrases like
`The ship has entered glide mode`. The intended style is still agency-safe, but
warmer: `We've entered glide` or `We're under fire` are acceptable shared-state
phrases, while `I jumped`, `I fired`, or `I docked` remain forbidden unless a
current direct command makes that appropriate.

### Current State Beats Memory

The shared assistant system prompt now explicitly says current status overrides
memories and prior conversation for live values:

- cargo
- location
- hull
- shields
- fuel
- destination

This was added after a restart/playtest case where Cassia appeared to combine a
historical cigar-hauling memory with the latest purchase event and inferred an
incorrect current cargo total.

Cargo inventory in status YAML is now labeled `CurrentCargoContents` instead of
`CargoContents` to make the live-state meaning harder for the model to miss.

### Gemini Tool History Fallback

Gemini native calls require real `thought_signature` data when prior assistant
messages contain tool calls. Some tool-call history can come from the
OpenAI-compatible fallback path, where only the placeholder
`skip_thought_signature_validator` is available.

Before this change, the native Gemini path could attempt the next request anyway
and receive a `400 INVALID_ARGUMENT` response:

`Function call is missing a thought_signature`

The model wrapper now detects prior tool history without real Gemini thought
signatures and skips directly to the OpenAI-compatible fallback for that turn.
This preserves behavior while avoiding an expected failed native request and its
latency.

## Observed Results

The initial playtest showed Cassia staying coherent through an engineer unlock
loop involving route plotting, station docking, rare commodity purchase, and
return trips.

Representative before/after snapshots from the test:

- Before context trim: `96` calls, `646.1K` total tokens, `383.8K` sent,
  `253.6K` cached.
- During context trim test: `89` calls, `579K` total tokens, `318.5K` sent,
  `255.1K` cached.
- Later session sample: `164` calls, `1.0M` total tokens, `572.8K` sent,
  `432.9K` cached, `0` thinking output.

The trim reduced uncached sent tokens in comparable samples while leaving cache
hits and Cassia's personality largely intact.

## Known Watch Points

Continue listening for these playtest issues:

- Cassia being too cold or repetitive with `the ship` phrasing.
- Vague answers when asked direct detail questions about stations, routes,
  cargo, engineers, modules, or missions.
- Incorrect live values caused by memory summaries overpowering current status.
- Unexpected `400` responses after tool calls.
- Any loss of route or engineer-unlock context during long ferry loops.

## Tests

Focused tests cover:

- core status retaining live ship/location context
- core status omitting heavy catalog sections
- full status retaining existing catalog sections
- detail selector switching to full for explicit catalog questions/events
- current cargo inventory being labeled as current
- Gemini cache behavior and reasoning config
- Gemini tool-history detection for missing thought signatures

Last local run:

```powershell
python -m pytest test\lib\test_GeminiCachedLLMModel.py test\lib\test_PromptGenerator.py -q
```

Result:

`26 passed`
