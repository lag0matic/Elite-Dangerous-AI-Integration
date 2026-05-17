# Focus Modes

Focus modes control how much game context COVAS:NEXT gives to the AI before it speaks. They are meant to reduce noisy, dashboard-like replies without making the AI blind to important events.

Focus modes do not change Elite Dangerous. They only change what information is sent to the language model.

## Why Focus Modes Exist

Elite Dangerous can produce many events at the same time: travel, docking, chat, mining, combat, cargo, system scan data, carriers, stations, friends, music, and more.

Without focus modes, the AI may try to mention too many unrelated facts in one reply. For example, it might answer a docking event while also talking about cargo, carriers, fuel, or old system data.

Focus modes narrow the AI's attention so it can respond to the most relevant subject.

## Manual Focus

You can switch focus by speaking naturally, for example:

- "Combat focus"
- "Switch to mining focus"
- "Travel focus"
- "Quiet mode"
- "Full context"
- "Normal focus"
- "What focus are you in?"

The selected manual focus stays active until you change it or restart the app. On restart, COVAS:NEXT returns to Normal focus.

The overlay can show the current focus under the avatar.

## Temporary Automatic Focus

COVAS:NEXT can also apply a temporary automatic focus for a single reply when the newest events clearly fit a narrower situation.

This is not the same as permanently switching your selected mode.

For example:

- A docking tool result may temporarily use Tool Result focus.
- A clear combat batch may temporarily use Combat Focus.
- A mining event may temporarily use Mining focus.

When this happens, the overlay may show an AUTO badge. The manual focus has not changed; only that reply used a temporary effective focus.

This avoids making the AI permanently switch modes because of one event that might be misleading.

## Reaction Overrides

The Reactions screen lets you control individual events for each focus profile.

Each event can be set to:

- React: the event is visible and can trigger a spoken reaction.
- See: the event is visible as context but does not force a reaction.
- Hidden: the event is removed from the AI prompt for that focus profile.

If an event has no profile-specific override, that focus mode uses its built-in defaults.

Changing the Global defaults does not automatically make Quiet or Combat Focus noisy. Profile overrides are explicit. A focus profile only changes when you edit that profile.

## Normal

Normal is the default broad mode. It behaves closest to the standard COVAS:NEXT event reaction system.

The AI can see normal memories, prior conversation, current status, and regular event context according to your global reaction settings.

Use Normal when you want the assistant to behave generally and you are not trying to reduce context for a specific activity.

## Full Context

Full Context gives the AI broad awareness for debugging or explicit situational awareness.

It can see broad status and event context. It is useful when you want the AI to answer broader questions, but it can also make replies more verbose or more likely to include unrelated details.

Use Full Context when you want maximum awareness and are willing to tolerate more chatter.

## Combat Focus

Combat Focus is designed to keep the AI on immediate tactical facts.

By default, it can see combat-relevant events such as:

- Combat entered or exited
- Under attack
- Target information
- Wanted, hostile, or enemy target details
- Bounty scans and bounty events
- Shield, hull, heat, cockpit breach, and death events
- Interdiction and escape events
- FSD charging or mass lock escape status

It uses compact ship status and avoids old memories, prior assistant replies, broad system chatter, economy data, cargo, exploration data, friends, Twitch, and routine status.

Important behavior: shield or hull damage alone is not treated as proof of combat. Collision or environmental damage can also cause shield and hull events. Combat Focus should not invent an attacker unless there is combat evidence such as UnderAttack, CombatEntered, hostile target data, hostile comms, or a bounty/kill event.

## Mining

Mining focus is designed for asteroid work, refinery activity, limpets, cargo, and nearby mining threats.

By default, it can see mining-relevant events such as:

- Prospected asteroids
- Refined materials
- Limpet launches
- Cargo collection and ejection
- Cargo scoop state
- Cargo and limpet reminders
- Reservoir replenishment
- Local, system, and NPC text chatter
- Nearby hostile or wanted target information
- Combat and damage events that matter while mining

Local and NPC chatter remains visible because pirates may announce themselves while you are mining.

Mining focus ignores broad exploration discoveries, station services, memories, prior assistant replies, broad travel history, and economy noise unless you explicitly override events.

## Travel / Docking / Exploration

Travel / Docking / Exploration focus is for route movement, jumps, arrival, supercruise, docking, scans, and discoveries.

By default, it can see events such as:

- FSD jumps and jump starts
- FSD target and route updates
- Supercruise entry and exit
- Destination drops
- Docking requests, grants, denials, timeouts, and docking state
- Undocking
- Location and carrier jump events
- Fuel scoop events
- Glide mode and high gravity warnings
- Discovery scans, FSS scans, body signals, scans, and codex entries
- Station, carrier, outpost, megaship, installation, beacon, signal, and resource extraction discoveries
- Local/system text that may matter during travel

It avoids mining, cargo, market, station-service, combat target churn, memories, and prior assistant replies unless they are directly relevant or explicitly overridden.

## Commerce

Commerce focus is for market and station-service results.

By default, it can see events such as:

- Market sells and buys
- Drone buys and sells
- Refuel, repair, restock, and ammunition purchases
- Voucher redemption
- Fine payment
- Powerplay merits and rank
- Cargo and limpet reminder events that directly relate to a transaction

For a market sale, the sale should be treated as the main subject. It should not be replaced by unrelated cargo capacity, limpets, station services, memories, or prior assistant replies.

## Quiet

Quiet mode is for reducing chatter.

By default, it only allows direct Commander speech, tool results, critical safety facts, and major verified results.

It can still allow major events such as:

- Under attack
- Shield, hull, heat, cockpit breach, and death events
- Docking granted or denied
- Docked and undocked
- FSD jump or jump start
- Supercruise entry and exit
- Major sell or buy events
- Low fuel, low health, or low oxygen warnings

Quiet mode does not inherit noisy global behavior unless you explicitly add profile overrides.

## Tool Result

Tool Result focus is temporary. It is used when a tool was just called and the reply should be about that tool result.

By default, it can see directly relevant tool-result events such as:

- Docking requested, granted, denied, cancelled, or timed out
- Cargo scoop, hardpoint, landing gear, light, night vision, and silent running state changes

It should not attach unrelated carriers, stations, ring contents, mining context, route state, FSD state, memories, or prior assistant replies to the tool result.

Focus-control tools are special. If you ask to switch focus, Tool Result focus should reply only about the focus change.

## Practical Tips

Use Normal for everyday play.

Use Mining when asteroid information, cargo, limpets, and pirate chatter matter more than broad system information.

Use Combat Focus when you want short tactical responses and less unrelated chatter.

Use Travel / Docking / Exploration when routing, arrival, scans, and docking are the main activity.

Use Commerce when selling, buying, repairing, refueling, or handling station services.

Use Quiet when you want the AI to speak only for important things.

Use Full Context when debugging or when you deliberately want broad awareness.

If a mode is hiding something you care about, add a profile override for that mode. If a mode is too noisy, hide the noisy event in that profile.
