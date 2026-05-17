# COVAS:NEXT Focus Profiles Roadmap

This document tracks the proposed Focus Profiles work for COVAS:NEXT/Cassia.

Goal: reduce LLM context overload by changing what the assistant sees based on the current task, without rewriting COVAS:NEXT or turning Cassia's prompt into a brittle wall of if/then rules.

## Problem

COVAS:NEXT can send the assistant a large mixed context bundle: game events, projected events, current status, memories, chat, route data, target data, market/economy data, and prior assistant replies.

Large instruct models can handle this in calm situations, but live combat exposed a failure mode:

- The model synthesized unrelated context into one reply.
- System/Twitch/trade chatter leaked into combat lines.
- Stale memory/status was treated as current.
- Friendly or ambiguous targets were treated as enemies.
- Combat replies became long, noisy, and tactically unreliable.

The fix should not be endless prompt surgery. The assistant should receive a smaller, task-appropriate page of reality.

## Concept

A Focus Profile is a named context policy.

It controls:

- Which event categories are visible to the LLM.
- Which events can trigger replies.
- Which status sections are included.
- Whether memories are included.
- Whether prior assistant replies are included.
- Whether a small profile-specific prompt note is appended.

Cassia remains Cassia. Focus Profiles only change what she can see and how much context she gets.

## Initial Profiles

### Normal

Purpose: preserve current COVAS:NEXT behavior.

Expected behavior:

- Use existing event reactions and status context.
- No special filtering beyond existing settings.
- Default manual profile.

### Combat-Focus

Purpose: keep autonomous combat replies tactical and current.

Visible context:

- Combat events.
- Current hostile/wanted/enemy target.
- Enhanced ship status: shields, hull/health if available, heat, pips, hardpoints, FSD/mass lock.
- Hostile/local NPC chatter when relevant.
- Confirmed combat rewards or kills.

Hidden context:

- Twitch chat.
- System trade chatter.
- Market/economy/community goal chatter.
- Exploration scans.
- Mining/cargo unless directly relevant to damage or escape.
- Memories.
- Prior assistant monologues.
- Friendly/lawless target churn unless actively hostile.

Prompt note:

Combat focus active. Speak only about the immediate threat, damage, heat, shields, target, escape state, or confirmed kill.

### Mining

Purpose: keep mining commentary useful without losing danger awareness.

Visible context:

- Mining events: prospector results, asteroid contents, asteroid cracked, refinery events.
- Cargo and limpets.
- Shields and hull if damaged or danger-related.
- Local/system chatter.
- Nearby threats.

Hidden context:

- Exploration firehose.
- Station service detail.
- Market detail unless the Commander asks or a sale/purchase event occurs.
- Memories by default.

### Travel / Docking / Exploration

Purpose: keep route, arrival, docking, and discovery commentary grounded.

Visible context:

- Ship update events.
- Docking events.
- Route/nav.
- Location/system information.
- Basic ship status.
- Exploration highlights.
- Local/system chatter.

Hidden context:

- Mining/refinery detail.
- Market/station service detail unless directly relevant.
- Combat target churn unless danger occurs.
- Memories unless directly asked.

### Commerce

Purpose: keep market, repair, refuel, restock, voucher, fine, and Powerplay transaction replies on the transaction itself.

Visible context:

- Market sales and purchases.
- Repairs, refuel, restock, ammo, drones.
- Vouchers, fines, Powerplay merits, and Powerplay rank.
- Directly resulting cargo state when relevant.

Hidden context:

- Prior assistant replies.
- Memories.
- Mining chatter.
- Station-service noise.
- Stale cargo capacity reminders.
- Travel, docking, and combat context unless directly relevant.

Prompt note:

Commerce focus active. For a sale, lead with what was sold, quantity, and total credits. Do not replace a sale with cargo capacity, limpets, station services, memories, or prior assistant replies.

### Quiet

Purpose: minimal chatter.

Visible context:

- Direct Commander speech.
- Tool results.
- Critical safety events.

Hidden context:

- Routine game events.
- Memories.
- Chatter.
- Broad status.

### Full-Context

Purpose: debugging, planning, or explicit broad situational awareness.

Visible context:

- Everything current COVAS:NEXT would normally include.

## Design Principles

- Start backend-first. UI comes after the behavior proves useful.
- Keep profiles coarse at first: category/status-section level, not hundreds of per-event toggles.
- Preserve existing reactions as the baseline.
- Separate manual profile from automatic temporary profile.
- Do not make the LLM infer profile from a noisy bundle when COVAS can select it more reliably.
- Prefer log visibility over guessing.
- Avoid hardcoding Cassia-specific personality into the profile engine.

## Manual vs Automatic Focus

Manual profile:

- User-selected persistent setting.
- Examples: Normal, Quiet, Full-Context, Mining.
- Can be changed by UI or a voice/tool action.

Automatic temporary profile:

- Chosen per reply from recent events.
- Does not permanently change the manual profile.
- Examples:
  - UnderAttack -> Combat-Focus for this reply.
  - CombatEntered -> Combat-Focus for this reply.
  - DockingGranted/DockingDenied -> Travel / Docking / Exploration for this reply.
  - ProspectedAsteroid/MiningRefined -> Mining for this reply.

Resolution:

1. Direct Commander speech and tool flows should usually use the manual profile or full normal context.
2. Critical danger can temporarily narrow the reply even when manual profile is Normal.
3. Full-Context should override most automatic narrowing, except possibly death/cockpit breach.

## Proposed Data Model

First pass can live in Python defaults. Later it can move to config/UI.

Example shape:

```json
{
  "focus_profiles": {
    "normal": {
      "mode": "default"
    },
    "combat-focus": {
      "event_categories": {
        "Combat": "on",
        "Social": "filtered",
        "Trading": "hidden",
        "Mining": "hidden",
        "Exploration": "hidden"
      },
      "status_sections": {
        "vehicle": "enhanced",
        "target": "on",
        "location": "minimal",
        "nav": "minimal",
        "friends": "hidden",
        "market": "hidden"
      },
      "memory": "hidden",
      "prior_assistant": "hidden",
      "prompt_note": "Combat focus active. Speak only about immediate threat, damage, heat, shields, target, escape state, or confirmed kill."
    }
  },
  "active_focus_profile": "normal"
}
```

Possible visibility values:

- `hidden`: do not send to model.
- `aware`: send to model but do not trigger reply.
- `react`: send to model and allow reply trigger.
- `filtered`: send only if it passes a category-specific filter.
- `summary`: send compact digest instead of raw events.

## Implementation Plan

### Phase 0: Inventory

- [x] Reset source tree to current upstream main.
- [x] Extract current reaction inventory from backend defaults and UI categories.
- [x] Save inventory in `FOCUS_PROFILE_REACTIONS_INVENTORY.md`.

### Phase 1: Backend Skeleton

- [x] Define Focus Profile names and default config in backend code.
- [x] Add active manual focus profile state with default `normal`.
- [x] Add profile resolution function:
  - manual profile
  - automatic temporary profile
  - final effective profile for this reply
- [x] Limit automatic profile selection to the newest pending event cluster so old backlog events do not steal focus.
- [x] Add debug logging of effective profile and reason.
- [x] Do not change UI yet.

### Phase 2: Prompt Filtering Engine

- [x] Add prompt context filtering before event messages are added.
- [x] Add status-section filtering.
- [x] Add memory inclusion/exclusion by profile.
- [x] Add prior-assistant inclusion/exclusion by profile.
- [x] Add profile prompt note.
- [x] Keep Normal behavior identical to upstream.

### Phase 3: Combat-Focus First Slice

- [x] Implement Combat-Focus profile.
- [x] Trigger automatically for `UnderAttack`, `CombatEntered`, severe shield/hull/heat events, and hostile/wanted/enemy target combat events.
- [x] Keep hostile target and current combat status.
- [x] Suppress system trade chat, Twitch chat, memories, economy, exploration, mining, and prior assistant monologues.
- [x] Log filtered event categories/counts.
- [x] Test against recorded combat logs.

### Phase 4: Manual Profile Tools

- [x] Add `set_focus_profile(profile)` action.
- [x] Add `get_focus_profile()` action.
- [x] Ensure tools are available only when COVAS tools are enabled.
- [x] Ensure Cassia reports verified profile changes only after the tool succeeds.
- [x] Add aliases for voice use:
  - combat focus
  - normal awareness
  - quiet
  - full context
  - mining focus

### Phase 5: Mining Profile

- [x] Implement Mining profile.
- [x] Keep prospector, refinery, cargo, limpets, shields, local/NPC/system chatter, and danger.
- [x] Hide unrelated exploration/station/economy noise.
- [ ] Playtest mining with Cassia.

### Phase 6: Travel / Docking / Exploration Profile

- [x] Implement Travel / Docking / Exploration profile.
- [x] Keep route, nav, docking, location/system info, basic status, exploration highlights.
- [x] Hide unrelated mining/station-service/market detail.
- [x] Add compact travel/docking/exploration status.
- [x] Test FSD charging, FSD jump, docking granted, and combat override against recorded logs.
- [ ] Playtest FSD jumps, docking, glide mode, and system arrivals.

### Phase 6B: Commerce Profile

- [x] Implement Commerce profile.
- [x] Trigger automatically for `MarketSell`, `MarketBuy`, refuel, repair, restock, voucher, fine, Powerplay merits, and Powerplay rank events.
- [x] Hide prior assistant replies, memories, stale cargo chatter, mining context, and station-service noise.
- [x] Replay platinum sale and verify the prompt leads with `MarketSell` only.
- [x] Add regression test that `MarketSell` outranks `RememberLimpets`.
- [ ] Live test another sale and verify Cassia reports quantity and total credits.
- [ ] Live test limpets/ammo/restock and verify she does not invent sale or cargo totals.

### Phase 7: Quiet and Full-Context

- [ ] Implement Quiet profile.
- [ ] Implement Full-Context profile.
- [ ] Confirm Full-Context matches or intentionally approximates current upstream behavior.

### Phase 8: UI

- [x] Add focus profile selector to the Reactions pane.
- [ ] Show current effective profile.
- [x] Add simple per-profile event override editor using existing blind/see/react controls.
- [x] Preserve global reactions as the fallback for profile overrides.
- [ ] Consider reworking reactions pane into a denser profile/category matrix.
- [ ] Avoid blocking backend work on UI polish.

## Open Questions

- Should automatic Combat-Focus override manual Full-Context during life-threatening events?
- Should direct Commander questions always bypass automatic focus, or only non-danger questions?
- Should local/system chat be split by channel/source before profile filtering?
- Should hostile NPC comms be classified separately from generic NPC/station chatter?
- Should profile configs live per character or globally?
- Should profile changes be remembered across restarts? Current answer: no, live focus resets to normal on restart.
- Should custom plugins be able to register profile categories or profile-specific context?

## Testing Checklist

### Synthetic

- [ ] Feed mixed combat + system chat + memory + status and verify only combat context reaches the prompt.
- [ ] Feed direct Commander question during combat and verify enough context remains to answer.
- [ ] Feed docking granted with unrelated status and verify no dashboard summary.
- [ ] Feed prospector result with chat noise and verify mining profile behaves.
- [x] Replay docking granted as single pending event and verify only docking context is visible.
- [x] Replay FSD jump as single pending event and verify travel focus is selected.
- [x] Replay mixed backlog with old combat events and verify recent event cluster controls automatic focus.
- [x] Unit test commerce focus vs limpet reminders.
- [x] Unit test non-pending Commander speech does not leak into automatic focus.
- [x] Unit test compact travel status returns structured state.
- [x] Unit test shield/hull damage still selects safety-focused context.

### Live Playtest

- [ ] Combat: wanted target scan.
- [ ] Combat: UnderAttack.
- [ ] Combat: shields down/up.
- [ ] Combat: heat warning/damage.
- [ ] Combat: target destroyed / bounty / merits.
- [ ] Mining: prospector result.
- [ ] Mining: refinery output.
- [ ] Mining: cargo full / limpets.
- [ ] Travel: FSD charging.
- [ ] Travel: FSDJump arrival.
- [ ] Docking: request granted/denied.
- [ ] Docking: docked/undocked.
- [ ] Commerce: sell mined commodity and verify quantity + total credits.
- [ ] Commerce: buy limpets/restock and verify transaction-specific reply.
- [ ] Travel: FSD charging after cargo question and verify no inventory hallucination.
- [ ] Damage: asteroid collision/shields down/hull loss and verify no invented attacker.

## Notes For Future Context

The user prefers architectural fixes over prompt hydras. They are comfortable testing live in Elite Dangerous VR and reporting logs, but wants COVAS/NPC context to remain rich when appropriate. Cassia's personality matters: she should remain vivid, profane, devoted, and in-universe, but operational reliability matters most during combat and docking.

This roadmap intentionally separates Cassia's voice from COVAS context policy.

## Current Implementation Snapshot

Last updated after live mining/travel/docking/sale testing on 2026-05-16.

Implemented code paths:

- `src/lib/FocusProfiles.py` defines automatic focus profiles for normal, combat-focus, mining, travel-docking-exploration, commerce, and tool-result.
- `src/lib/PromptGenerator.py` applies focus filtering, compact status generation, and profile prompt notes.
- `setFocusProfile` and `getFocusProfile` actions expose manual focus control by voice/tool call.
- Character config now supports per-profile event reaction overrides via `focus_profile_reactions`.
- The Reactions pane can edit Global defaults or focus-profile-specific overrides. In profile mode, explicit overrides win over global defaults; clearing an override falls back to global.
- `tools/replay_focus_prompt.py` can replay a DB row and show the exact filtered prompt.
- `tools/inject_receive_text.py` can append synthetic `ReceiveText` journal events for local/NPC chatter tests.
- `test/lib/test_FocusProfiles.py` covers the key focus regressions found during live testing.

Live regressions discovered and patched:

- Travel focus returned `null` because `compact_travel_status()` did not return its built travel state. Fixed.
- Old Commander questions leaked into automatic focus prompts, causing FSD commentary to hallucinate inventory state. Fixed by only including pending user speech in non-normal profiles.
- Shield/hull crash damage was treated like combat with an invented attacker. Combat prompt note now says shield/hull damage alone may be collision or environmental damage unless attack/combat/hostile evidence is present.
- `MarketSell` was handled by normal context and got buried under stale cargo/limpet chatter. Added commerce focus.
- `MarketSell` could still lose focus priority to `RememberLimpets` in a station batch. Commerce now outranks mining reminders, and `MarketSell` is the highest-priority commerce trigger.
- Historic startup events were previously inserted as pending short-term context. Historic catch-up now updates projections but does not become pending reply context.
- Location projection carried stale station/body/ring data across jumps. Local context now clears on location/supercruise/jump transitions.
- Travel fuel status now labels main fuel as tons and computes percent when capacity is available.

Known behavior to keep watching:

- `InDanger` is vague. It should be visible as caution, but should not imply pirates, combat, shields, or hull unless another event confirms it.
- Damage bursts can arrive in several hull events within a second. The first reply may still race ahead of the final hull value unless batching/debounce is added later.
- Local/NPC chatter in mining is currently visible context, not always a must-react trigger. Mode-specific blind/see/react controls are the likely long-term UI solution.
- Qwen can still overfit to stale assistant phrasing if a profile accidentally includes prior assistant replies.
