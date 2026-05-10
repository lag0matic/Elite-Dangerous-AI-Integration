# Qwen Context Pack Plan

Working note for the Qwen/Cassia context redesign. Goal: keep Cassia informed without sending full historical/system noise or hand-trimming every event into brittle one-off summaries.

## Guiding Principles

- Preserve the triggering event as the source of truth.
- Remove unrelated surrounding noise instead of compressing the event itself.
- Use existing event reaction categories as the routing layer.
- Send stable encyclopedia data only when relevant, not on every telemetry turn.
- Use current projections/state for live answers instead of relying on conversation memory.
- Pull long-term memories only when the user asks about history, recall, or past sessions.
- Prefer category-level context packs over per-event special cases.

## Action Checklist

- [x] Map backend event names to the existing UI reaction categories.
- [x] Identify where automatic event reactions build prompts today.
- [x] Separate prompt builds into two paths:
  - [x] user/command prompt path identified with prompt build mode
  - [x] automatic telemetry reaction path identified with prompt build mode
  - [x] apply different context selection by prompt build mode
- [x] For automatic telemetry, remove default long-term memory injection.
- [x] For automatic telemetry, remove full status/system encyclopedia injection by default.
- [x] Preserve existing `event_message()` output for the triggering event.
- [x] Add a small always-on core status pack.
- [x] Add category context packs.
  - [x] Mining
  - [x] Stations / Docking
  - [x] Ship Updates / FSD
  - [x] Combat
  - [x] Exploration / System
  - [x] Social
  - [x] Trading / Missions
- [x] Add tests that inspect the prompt shape for representative events.
- [x] Add debug logging that shows which category pack was attached.
- [x] Playtest with Qwen and capture bad cases before adding more rules.
- [x] Extract context pack builders out of `PromptGenerator.py`.

## Current Implementation Status

Implemented in this branch:

- Backend category mapping mirrors the UI Event Reactions categories.
- Prompt builds are split into `user_command` and `automatic_telemetry` modes.
- Automatic telemetry uses a compact core status pack plus one routed category pack.
- Automatic telemetry no longer receives the full status/system encyclopedia by default.
- Automatic telemetry no longer receives long-term memory by default.
- User/command prompts still use the old fuller context path for now, including tools and memories.
- Triggering event text still comes from the existing event message templates.
- Category packs currently cover Mining, Stations/Docking, Ship/FSD, Combat, Exploration/System, Social, and Trading/Missions.
- Focused prompt-shape tests cover representative category events and the mode split.

Not done yet:

- Qwen playtest pass on the cleaned prompt shape.
- Tool prompt slimming and tool-use-specific context packs.
- Direct tests for the tool-use plan.
- On-foot and SRV-specific context packs. These currently fall back to core status unless routed through an existing broader category.

## Core Status Pack

Small current-truth footer attached to most automatic reactions.

- Ship name/type
- Location: system and station/body/ring when relevant
- Mode: docked, landed, supercruise, normal space, on foot, SRV, fighter
- Danger/combat flag
- FSD state when active
- Cargo count/capacity
- Fuel when relevant
- Shields/hull only when relevant or abnormal

## Category Packs

Each pack should be concrete enough to implement from projections and event payloads. "When relevant" means one of:

- the triggering event directly references the field
- the user asked about that category
- the value is abnormal or operationally important
- the value disambiguates the event result

Avoid vague catch-alls. If a pack needs more data later, add a named field to the pack rather than relying on the LLM to infer from unrelated context.

### Mining

Use for prospector, refinery, collector, cargo scoop, mining fragments, limpets.

- Triggering mining event, mostly intact
- Current mining mode/context:
  - current ring/body/hotspot destination
  - mining ship flag
  - hardpoints/cargo scoop state
- Cargo and capacity:
  - total cargo/capacity
  - mined commodity counts
  - limpet count
  - refinery/cargo full state if available
- Limpets/drones:
  - prospector launched/active/current target if known
  - collectors launched/active if known
  - failed/expired drone events if present
- Prospector payload:
  - material content Low/Medium/High
  - minerals remaining
  - all asteroid materials and percentages
  - motherlode/core material if present
- Refinery payload:
  - refined material
  - updated cargo total if current
- Local risk:
  - danger/combat flag
  - pirate/target only if active or just changed

### Combat

Use for attacks, target changes, bounty, shields, hull damage, combat music projections.

- Triggering combat event
- Current target:
  - pilot/name
  - ship type
  - legal status
  - bounty
  - faction/power if known
  - scan status
  - subsystem target if known
- Ship survivability:
  - shields up/down/percent if available
  - hull percent
  - heat
  - module damage if the triggering event is damage-related
- Weapons/combat posture:
  - hardpoints deployed/stowed
  - fire group
  - selected weapon if available
  - pips
- Tactical context:
  - hostile count/threat if available
  - wing status/wingmate target only if wing/combat-relevant
  - bounty/kill bond/redeemable value when event is reward-related

### Stations

Use for docking, undocking, station services, no-fire, pad, approach, market/outfitting.

- Triggering station/docking event
- Station identity:
  - station/carrier name
  - station type
  - system
  - controlling faction/government/economy if available
- Docking flow:
  - docking requested/granted/denied/cancelled/timeout
  - assigned pad and clock orientation if available
  - no-fire zone
  - in docking range
  - landing gear state
  - docking computer state
  - mass lock if active
- Station services:
  - market/outfitting/shipyard/repair/refuel/rearm availability when event/user question needs it
  - currently open service screen such as Market, Outfitting, Shipyard
- Market/outfitting local detail:
  - current station market/outfitting data only when asked or when event is market/outfitting
  - avoid full unrelated station lists

### Ship Updates

Use for fuel, heat, FSD, landing gear, cargo scoop, hardpoints, night vision, pips, repairs.

- Triggering ship-state event
- Ship basics:
  - ship name/type
  - current mode: normal space, supercruise, docked, landed, SRV, fighter, on foot
- FSD/navigation:
  - charging/cooldown/mass locked/supercruise state
  - destination/route target
  - jump range only when asked or jump planning
- Systems:
  - fuel main/reservoir and low fuel flag
  - heat/overheating
  - shields
  - hull
  - oxygen/life support if relevant
- Controls/posture:
  - landing gear
  - cargo scoop
  - hardpoints
  - lights/night vision
  - silent running
  - pips
- Maintenance:
  - repair/refuel/rearm result and cost
  - ammo/restock state if available

### Exploration / System

Use for FSD jumps, scans, discoveries, codex, bodies/signals, system arrival.

- Triggering exploration/system event
- System arrival:
  - system name
  - allegiance/government/security/economy
  - controlling faction and state
  - population
  - primary star and scoopable flag
  - legal status if changed
- Navigation:
  - current route and jumps remaining
  - destination target/body/station
  - jet cone boost state if active
- Scans/discoveries:
  - body name/type
  - valuable body estimates if event includes them
  - biological/geological/human signal counts
  - codex entry details
  - first discovery/mapped flags if present
- Local system summary:
  - station/carrier counts
  - HGE/high-grade material candidates
  - noteworthy bodies/signals
  - full body/station lists only on direct request

### Social

Use for friends, wing, chat, Twitch.

- Triggering social event
- Friends:
  - friend name and new status from event
  - current online friends list
  - online count
- Wing/team:
  - wing joined/left/member added
  - current wing members if available
  - nav lock status if available
- Text/comms:
  - sender
  - channel
  - message text
  - sender relation when known
- Twitch:
  - chatter name
  - message text
  - recent mentions only when asked or event is Twitch-related

### Trading / Missions

Use for market buys/sells, mission accepted/completed, cargo transfer.

- Triggering trade/mission event
- Market transactions:
  - commodity/material/module/ship name
  - count
  - unit price
  - total sale/cost
  - profit if event supplies average price paid
  - black market/stolen/illegal flags
  - station/market name
  - total balance after transaction when current status supplies it
- Cargo:
  - current cargo/capacity
  - cargo contents summary
  - mission cargo flag
  - stolen/illegal cargo flags
  - cargo transfer/eject/collect details
- Missions:
  - mission type/name
  - faction
  - destination system/station/body
  - target commodity/passenger/kill/delivery details
  - reward/bonus/fine
  - influence/reputation effects if present
  - expiry/time remaining
  - mission status: accepted, redirected, completed, failed, abandoned
  - active mission count and matching active mission only when needed
- Powerplay/community goals:
  - merits/contribution/reward/rank when the triggering event is powerplay/CG-related
  - do not attach CG status to ordinary trade events unless asked

## Context Selection Rules

## Current Prompt Flow Findings

This branch starts from the current shared prompt path. The important shape is:

- `Assistant.reply_thread()` gathers short-term memory with `event_manager.get_short_term_memory(150)`.
- It treats events with `responded_at is None` as pending/new.
- It always asks `PromptGenerator.generate_prompt(events, projected_states, pending_events, memories)` for the full LLM prompt.
- `PromptGenerator.generate_prompt()` currently mixes:
  - up to 20 recent game/status/projected/external/quest event messages
  - up to 50 recent conversational pieces total
  - tool request/response messages
  - the full generated status message
  - latest long-term memories
  - the system/character prompt
- Tool availability is decided after prompt generation in `Assistant.reply_thread()`.
- Tools are enabled only when the pending reasons include a user turn or tool result.
- Automatic telemetry reactions and user/tool turns therefore share the same prompt builder today.

Implications:

- The first real behavior split should happen before or inside `PromptGenerator.generate_prompt()`, not inside individual event templates.
- Automatic telemetry can receive a slimmer context without touching user commands.
- User commands should keep tool definitions and current compact status, because natural phrasing still needs the LLM to interpret commands.
- Long-term memories should be gated by turn type; automatic telemetry should not receive them by default.
- The existing `event_message()` and `status_messages()` templates should stay intact at first, because they preserve the raw triggering event detail.

- Automatic telemetry:
  - system prompt
  - recent dialogue, small window
  - triggering event
  - core status pack
  - one category pack
  - no long-term memories by default

- User asks current-state question:
  - system prompt
  - recent dialogue
  - current compact status
  - relevant projection/category pack
  - no long-term memories unless needed

- User asks historical question:
  - system prompt
  - recent dialogue
  - current compact status if relevant
  - retrieved memories/logbook entries

- User gives tool/action command:
  - system prompt
  - recent dialogue
  - current compact status needed for tool selection
  - tool definitions
  - avoid unrelated memories/system encyclopedias

## Tool Use Plan

Tool calls are their own prompt path. They should not use the automatic telemetry context pack path.

### Goals

- Let natural phrasing still reach the LLM for tool choice.
- Keep enough current state for the model to choose the right tool and arguments.
- Avoid unrelated memory/system noise that distracts from tool use.
- Never let Cassia claim a tool result that was not confirmed by a tool response or later game event.

### Tool Prompt Shape

For user/action commands, send:

- system/Cassia prompt
- recent dialogue, small window
- current compact status required for action choice
- optional action-relevant category pack
- available tool definitions
- the user's command

Do not send:

- long-term memories unless the command explicitly depends on past knowledge
- full local-system encyclopedia unless route/search action needs it
- automatic telemetry event backlog
- unrelated generated UI history unless the command is about UI

### Tool Context Packs

Attach only the pack needed for the likely tool family.

- Ship controls:
  - ship mode
  - FSD/mass lock/supercruise/docked state
  - landing gear/cargo scoop/hardpoints/night vision
  - pips and fire group
- Docking:
  - station/carrier name
  - in docking range
  - no-fire zone if known
  - existing docking request state if known
  - docking computer availability
- Navigation:
  - current system
  - current route target/jumps
  - current destination
  - ship mode/FSD state
- Music:
  - current track/artist/playback state
  - Spotify device state if available
- Search/web agent:
  - user's query
  - current location/system/station/cargo/ship if useful
  - current task/goal if present
  - no full event history unless query asks for history
- Generative UI:
  - current overlay/component state
  - user's requested UI change
  - no gameplay/system encyclopedia unless the UI request needs it
- Twitch:
  - target channel/message/user
  - recent chat only when requested or moderation context needs it

### Tool Result Handling

- If the LLM returns a tool call, execute the tool and append the tool result.
- After tool result, let Cassia report only confirmed result data.
- If a later game event confirms the result more specifically, prefer the game event.
- If the tool fails, Cassia should say the failure plainly and not invent success.
- If no matching tool is available, say `Could not confirm, Commander.`

### Direct Action Guardrails

- For commands like docking, route plotting, music, UI edits, pips, gear, hardpoints, night vision, cargo scoop, or FSD:
  - a matching available tool must be called
  - text-only confirmation is not enough
  - success wording requires a tool result or game event
- Read-only status questions are not tool commands:
  - credits
  - cargo
  - fuel
  - hull/shields
  - location
  - friends online
  - current route/destination when already in current state

### Test Cases

- [x] "Request docking" produces `requestDocking` when available. (manual playtest)
- [x] "Request duck" still reaches docking tool via LLM interpretation. (manual playtest)
- [x] "Drop the legs" produces `landingGearToggle`. (manual playtest)
- [ ] "Kick the tires and light the fires" reaches FSD/jump behavior if context supports it.
- [x] "Play Nova by VNV Nation" produces `covasify_play` with track/artist arguments. (manual playtest via different Spotify song)
- [x] Tool failure does not become success text. (manual playtest)
- [x] Tool success reports only confirmed result. (manual playtest)
- [x] "How many credits?" does not call a tool. (manual playtest)
- [x] "Who is online?" does not call a tool and uses current Friends projection. (manual playtest)

## Test Cases

- [x] Prospector scan prompt includes all asteroid materials and mining pack, but not full system encyclopedia. (manual playtest)
- [x] Friend online event includes current friend state, but not mining/station/system data. (manual playtest)
- [x] Supercruise exit includes destination/location context, but not older StartJump text. (manual playtest)
- [x] Docking granted includes station and pad, but not community goals or local body lists. (manual playtest)
- [x] "Who is online?" pulls current Friends projection. (manual playtest)
- [x] "How many ground stations are in this system?" pulls local system/stations pack on demand. (manual playtest)
- [x] "What did we do last?" pulls memories/logbook entries. (manual playtest)
- [x] "How many credits?" uses current status balance, not transaction totals or memory. (manual playtest)
