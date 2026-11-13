# Seated Recenter and OBS Browser Source

Branch: `codex/seated-recenter-obs-browser-source`.

Based on `codex/seated-vr-anchor`. The recenter and electron-vr branches are unchanged.

## Controls

- Game Overlay: Off, Flatscreen, or VR. No Both or standalone-window option.
- OBS Browser Source: independent toggle, localhost port and copy-URL button.
- OBS canvas: 1920 x 1080, transparent; use those dimensions in OBS Browser Source.

Flatscreen uses the existing game-following desktop overlay. VR retains native
curvature, seated anchoring, offset updates and the EDVR logfile adapter.
OBS can run with either mode or with the game overlay Off. It creates no desktop
window and makes no LLM/TTS requests.

## Implementation

| Files | Change |
| --- | --- |
| `electron/obs-source.js` | Local HTTP/SSE server and bounded render-state snapshot. |
| `electron/index.js` | Observe backend output, control the independent source, remove combined rendering. |
| `electron/overlay-modes.js` | Normalize legacy modes. |
| `ui/src/app/components/obs-source-settings/` | Toggle, port, status and copy URL. |
| General/advanced settings components | Offer only Off/Flatscreen/VR and shared appearance controls. |
| Config/Tauri services | Normalize old configurations and expose source controls. |
| `electron/vr-overlay-updates.js` | Retain in-place updates for the remaining VR mode. |

The source reuses the overlay renderer with an injected read-only transport.
Connecting or refreshing replays the current avatar configuration, GenUI, merged
projected states, recent captions and animation state. Live events then update it.
Disconnecting hides stale content; reconnecting restores the current snapshot.

The server binds only to 127.0.0.1. An unguessable persistent URL token scopes
access. There is no command endpoint or backend stdin connection. Configuration
is allowlisted; provider keys, character prompts, plugin settings and logs are
not forwarded. Avatar routes expose only registered image references.

OBS preferences and URL token are stored separately under the app profile as
`obs-source-token.settings.json` and `obs-source-token`. They do not require
changes to the Python backend. Old Both mode migrates to VR plus OBS enabled,
unless an explicit OBS preference already exists. Old standalone/screen modes
migrate to Flatscreen. The source URL stays stable across restarts.

## Checks

`test/electron/obs-source.test.js` covers snapshot replay, credential filtering,
read-only requests, origins, avatar delivery, persistence and port conflicts.
Existing recenter tests remain in place. The UI build and hidden browser checks
cover real AVIF rendering, transparency at 1920x1080, live GenUI, refresh replay,
mode choices, independent OBS output, and URL copying.
