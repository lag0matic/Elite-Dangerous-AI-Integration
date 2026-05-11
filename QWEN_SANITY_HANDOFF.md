# Qwen Sanity Handoff

Date: 2026-05-11
Workspace before reinstall: `C:\Users\lag0m\Documents\CovasVR`
Branch: `Qwen_Sanity`
Remote: `origin/Qwen_Sanity`

## Current State

This branch is the personal/Qwen-focused COVAS:NEXT build for Cassia. The goal was to keep her voice/model behavior but stop the backend from drowning her in stale or irrelevant telemetry.

Latest pushed code commit before this handoff document:

`c781194 Ensure pytest is installed in CI`

Recent relevant commits:

- `c781194` Ensure pytest is installed in CI
- `602d7d7` Ignore historic replay for memory
- `26e5338` Prioritize urgent combat context
- `5036fd5` Filter stale telemetry prompt events
- `1e9ebf2` Record Qwen playtest checklist results
- `a15dbf2` Harden context packs during startup
- `55a4f2c` Omit inactive heat and fuel cues from ship context
- `64c34db` Limit telemetry prompt history to pending events
- `73a17b6` Add Qwen telemetry context packs
- `a833f2e` last commit that belonged on the clean streamer-mode line before Qwen-specific work

Local uncommitted files at handoff:

- `electron/index.js`
  - Dev-only override used to launch the repo frontend while pointing backend cwd/config/data at the live AppData folder.
  - Do not blindly commit unless you intentionally want this behavior.
- `patch-installed-vr-curvature.ps1`
  - Local helper script for patching installed VR curvature work.
- `qwen-sanity-dev.pid`
  - Runtime helper file only.

## What We Changed

### Context Packs

The main work is in `src/lib/ContextPacks.py` and `src/lib/PromptGenerator.py`.

Automatic telemetry now sends compact category-specific context instead of the entire galaxy every time:

- Core status pack
- Mining pack
- Station/docking pack
- Ship/FSD pack
- Combat pack
- Exploration/system pack
- Social pack
- Trading/mission pack

The intent is: Cassia gets enough relevant state to react intelligently, but not a huge pile of unrelated stations, bodies, powers, friends, music, cargo, and old events.

### Stale Telemetry Filtering

`5036fd5` fixed stale assistant/event contamination:

- Automatic telemetry now uses only relevant pending telemetry.
- Stale pending telemetry more than about 90 seconds older than the newest item gets dropped.
- This helped stop old events from resurfacing in new replies.

### Combat Context Priority

`26e5338` fixed an important combat bug:

- Before this, a ship/FSD event like `FsdMassLockEscaped` could steal the context pack from `UnderAttack` or `HeatWarning`.
- Cassia then got combat pressure without a clean combat frame and invented stuff like "three hostiles."
- Urgent combat events now preempt Ship/FSD context.
- Combat context includes a note not to invent hostile counts unless explicitly listed.

### Historic Replay Memory Fix

`602d7d7` fixed startup/journal replay becoming memory:

- On startup, COVAS reads the latest Elite journal file from the beginning as historic replay.
- Previously those historic events were inserted into `events_v1` as unmemorized, so the summarizer could turn the replay into new long-term memory after a database wipe.
- Historic replay events are now inserted with `memorized_at` and `responded_at` already set.
- They still rebuild projections/current state, but they should not become conversation, reply context, or long-term memories.

### CI Fix

`c781194` made the Windows and Linux workflows explicitly install:

`pytest==8.3.3 pytest-timeout==2.3.1`

This was added because GitHub Actions failed with:

`python.exe: No module named pytest`

## Tests

Last full local verification before handoff:

`103 passed, 3 warnings`

Command used:

`$env:PYTHONPATH='.'; pytest -q`

Warnings were dependency warnings from `speech_recognition`/`pygame`, not failures.

## Playtest Status

Good results seen:

- Tool use worked:
  - `Request docking`
  - STT-mangled `Request duck`
  - `Drop the legs`
  - music commands like `Play Sho Me Your Goblin on Spotify`
- Read-only status queries worked:
  - credits/balance
  - cargo
  - online friends
  - "What did we do last?"
- Mining was mostly good:
  - Prospector scan included useful mining context.
  - Cargo/status stayed mining-focused.
  - Some "low material content" wording was imperfect but acceptable.
- Docking improved:
  - Pad orientation/details worked.
  - Station spam was much reduced.
- Combat was improved after the urgent combat patch, but needs more long-session testing.

Things to keep watching:

- Cassia may still occasionally overstuff replies if the event burst is dense.
- She may occasionally append a trailing question, especially after combat/choice moments.
- Combat should be tested for at least one real session after the new build includes `26e5338` and `602d7d7`.
- If installed app behaves worse than dev, check whether installed backend actually contains the latest `resources\Chat\_internal\lib\*.py`.

## AppData To Preserve Before Windows Reinstall

Main live app data folder:

`C:\Users\lag0m\AppData\Roaming\com.covas-next.ui`

Important files/folders:

- `config.json`
  - Main settings, model/provider config, Cassia prompt, keys, behavior settings.
- `covas.db`, `covas.db-wal`, `covas.db-shm`
  - Database with events, memories, projections, GenUI entries, usage, etc.
- `plugins`
  - Installed plugins.
- `userAssets`
  - User assets.
- `logs`
  - Useful if debugging after restore.
- `blob_storage`, `IndexedDB`, `Local Storage`, `Session Storage`
  - Electron/browser storage; probably not all critical, but easiest to preserve.

Recommended backup before reinstall:

Copy the entire folder:

`C:\Users\lag0m\AppData\Roaming\com.covas-next.ui`

Also preserve the repo if possible:

`C:\Users\lag0m\Documents\CovasVR`

At minimum, after reinstall:

1. Clone repo.
2. Checkout `Qwen_Sanity`.
3. Restore `config.json`.
4. Restore `plugins`.
5. Restore `userAssets`.
6. Decide whether to restore `covas.db`.

If wanting a clean Cassia after reinstall, do not restore old `covas.db`, or restore it and wipe memory/events again.

## Memory Wipe Notes

We made a manual backup before wiping memory:

`C:\Users\lag0m\AppData\Roaming\com.covas-next.ui\covas.before-memory-wipe.20260510-185601.db`

The wipe preserved:

- `config.json`
- plugins
- GenUI/HUD entries (`genui_code_v1`)
- action cache
- projections/current state
- usage history

The wipe cleared:

- `events_v1`
- `memory_v1`
- `memory_vec_keywords_v1`
- vector memory backing tables

After that wipe, the app recreated memory from historic journal replay. That is why `602d7d7` exists.

If doing a fresh wipe after the latest build:

1. Fully stop COVAS and backend.
2. Back up `covas.db`, `covas.db-wal`, `covas.db-shm`.
3. Clear only memory/conversation tables.
4. Start the new build that includes `602d7d7`, so historic replay should not summarize itself again.

## Dev Launch Notes

A local dev override was added but not committed:

`electron/index.js`

Purpose:

Run the dev frontend from the repo while pointing the backend cwd at live AppData:

`COVAS_DEV_BACKEND_CWD=C:\Users\lag0m\AppData\Roaming\com.covas-next.ui`

Previous launch pattern:

```powershell
$env:COVAS_DEV_BACKEND_CWD="$env:APPDATA\com.covas-next.ui"
$env:NODE_ENV="development"
npm start
```

When this was working, backend logs showed it loaded files from:

`C:\Users\lag0m\AppData\Roaming\com.covas-next.ui`

Dev logs previously used:

- `qwen-sanity-dev.stdout.log`
- `qwen-sanity-dev.stderr.log`

These are local runtime artifacts only.

## Installed Build Notes

Installed app path observed:

`C:\Users\lag0m\AppData\Local\Programs\covas-next`

Packaged backend path observed:

`C:\Users\lag0m\AppData\Local\Programs\covas-next\resources\Chat\_internal\lib`

Important lesson:

The dev copy was good because it ran the repo source. The installed copy went off the rails because its packaged backend did not yet include the latest source fixes.

If the installed app behaves badly after reinstall, verify these exist in packaged backend:

- `PromptGenerator.py` has `_automatic_telemetry_events`
- `ContextPacks.py` has `_has_urgent_combat_event`
- `EventManager.py` marks historic events as already memorized/responded

## Current Prompt Direction

Cassia's prompt was simplified and tuned for Qwen:

- Keep her in-universe.
- Do not say NPC/player/game/in-game.
- Tool commands must call tools when available.
- Read-only state questions are not tool commands.
- Avoid invented state.
- Responses should have one primary subject and at most one closely related supporting fact.
- Salty/adult voice is okay, but avoid slurs, childish shock humor, and stacked metaphors.
- No generic handoff phrases like "your call," "your move," "if you want," etc.

Current prompt lives in AppData `config.json`, not necessarily in source.

## Provider/Model Notes

Voice/chat model:

- Qwen on DeepInfra/OpenRouter/Together-style endpoint was much better for Cassia's voice than Gemini Flash/Lite.
- Model in recent logs:
  - `Qwen/Qwen3-235B-A22B-Instruct-2507`

Observed strengths:

- Very natural Cassia voice.
- Good lewd/violent/salty tone.
- Better than Gemini Flash Lite for prompt adherence and personality.
- Very cheap compared with Gemini Flash.

Observed issues:

- Can over-narrate if flooded.
- Can invent tactical counts if combat context is vague.
- Can become noir/scene-setting if old/full context slips in.

Agent/search model:

- GPT-5.4-mini/nano was discussed for agent/search/GenUI.
- Nano seemed possibly too weak for complicated searches.
- Mini was considered acceptable because GenUI/search is infrequent.

## Next Steps After Reinstall

1. Clone repo and checkout:

```powershell
git clone https://github.com/lag0matic/Elite-Dangerous-AI-Integration.git
cd Elite-Dangerous-AI-Integration
git checkout Qwen_Sanity
```

2. Restore AppData:

```powershell
# Copy backed-up com.covas-next.ui folder back to:
$env:APPDATA\com.covas-next.ui
```

3. Install dependencies as needed:

```powershell
npm install
pip install -r requirements.txt
```

4. Pull the latest GitHub artifact/build from `Qwen_Sanity`, or run dev from source.

5. Test in this order:

- Startup: make sure she does not summarize the whole journal replay.
- "Who is online?"
- "How many credits?"
- "What do we have on board?"
- Music command.
- Docking command.
- Gear command.
- Prospector scan.
- Supercruise exit near station/carrier.
- Combat scan/under attack/shields/heat.

6. If Cassia says things that sound like old memories right after startup:

- Check `events_v1` and `memory_v1`.
- Confirm installed backend includes `602d7d7`.
- Confirm the running backend is not an old packaged copy.

## Useful Commands

Check branch and status:

```powershell
git branch --show-current
git log --oneline -12
git status --short
```

Run tests:

```powershell
$env:PYTHONPATH='.'
pytest -q
```

Inspect AppData DB tables:

```powershell
@'
import sqlite3, os
path = os.path.join(os.environ['APPDATA'], 'com.covas-next.ui', 'covas.db')
con = sqlite3.connect(path)
cur = con.cursor()
for name in ['events_v1','memory_v1','genui_code_v1','projections_v1']:
    print(name, cur.execute(f"select count(*) from {name}").fetchone()[0])
con.close()
'@ | python -
```

Find running backend:

```powershell
Get-Process | Where-Object { $_.ProcessName -match 'COVAS|Chat|electron|node|python' } | Select-Object Id,ProcessName,Path
```

## Final Mental Model

The good architecture is:

- Journal replay rebuilds state.
- Pending live telemetry drives Cassia's automatic reactions.
- Category context gives her relevant detail.
- Memories are only real summaries of actual play/conversation, not startup replay.
- User commands still get enough current status and tools to be flexible.

If she drifts, check which boundary failed:

- Too much old context: prompt generator/event filtering.
- Wrong context pack: context pack priority.
- Startup summary: historic replay memory handling.
- Tool refusal: command/tool prompt or action registration.
- Installed/dev mismatch: packaged backend is stale.
