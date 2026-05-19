from dataclasses import dataclass, field
from typing import Any, Literal

from .Event import (
    ConversationEvent,
    Event,
    ExternalEvent,
    GameEvent,
    MemoryEvent,
    ProjectedEvent,
    QuestEvent,
    StatusEvent,
    ToolEvent,
)
from .Projections import ProjectedStates, get_state_dict


FocusProfileName = Literal[
    "normal",
    "combat-focus",
    "mining",
    "travel-docking-exploration",
    "commerce",
    "quiet",
    "full-context",
    "tool-result",
]


@dataclass(frozen=True)
class FocusProfile:
    name: FocusProfileName
    prompt_note: str = ""
    include_memories: bool = True
    include_prior_assistant: bool = True
    include_non_pending_events: bool = True
    compact_status: bool = False
    allowed_events: set[str] = field(default_factory=set)
    allowed_status_events: set[str] = field(default_factory=set)
    allowed_target_legal_statuses: set[str] = field(default_factory=set)
    max_events_per_name: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class EffectiveFocusProfile:
    profile: FocusProfile
    reason: str
    automatic: bool


DEFAULT_FOCUS_PROFILES: dict[FocusProfileName, FocusProfile] = {
    "normal": FocusProfile(name="normal"),
    "full-context": FocusProfile(
        name="full-context",
        prompt_note=(
            "Focus profile: full-context. Broad context is visible for debugging or explicit situational awareness. "
            "Still answer from the newest verified data first and do not invent missing facts."
        ),
    ),
    "combat-focus": FocusProfile(
        name="combat-focus",
        include_memories=False,
        include_prior_assistant=False,
        include_non_pending_events=False,
        compact_status=True,
        allowed_events={
            "CombatEntered",
            "CombatExited",
            "UnderAttack",
            "ShipTargeted",
            "Bounty",
            "BountyScanned",
            "FactionKillBond",
            "ShieldState",
            "HullDamage",
            "HeatWarning",
            "HeatDamage",
            "Died",
            "CockpitBreached",
            "FsdCharging",
            "FsdMassLockEscaped",
            "BeingInterdicted",
            "Interdicted",
            "EscapeInterdiction",
        },
        allowed_status_events={
            "InDanger",
            "OutofDanger",
            "FsdCharging",
            "FsdMassLockEscaped",
            "LowHealthWarning",
            "LowOxygenWarning",
        },
        allowed_target_legal_statuses={"Enemy", "Wanted", "Hostile"},
        max_events_per_name={
            "UnderAttack": 2,
            "ShipTargeted": 2,
            "BountyScanned": 2,
            "Bounty": 2,
            "CombatEntered": 1,
            "CombatExited": 1,
            "InDanger": 1,
            "OutofDanger": 1,
        },
        prompt_note=(
            "Focus profile: combat-focus. Reply only about the most urgent current combat fact: "
            "incoming fire, damage, heat, shields, hostile target, escape state, or confirmed kill. "
            "Shield or hull damage alone may be collision or environmental damage; do not infer an attacker unless "
            "UnderAttack, CombatEntered, hostile target, hostile comms, or a bounty/kill event is present. "
            "Ignore system chat, Twitch chat, trade chatter, memories, economy, cargo, exploration, friends, and routine status."
        ),
    ),
    "mining": FocusProfile(
        name="mining",
        include_memories=False,
        include_prior_assistant=False,
        include_non_pending_events=False,
        compact_status=True,
        allowed_events={
            "ProspectedAsteroid",
            "MiningRefined",
            "LaunchDrone",
            "EjectCargo",
            "CollectCargo",
            "Cargo",
            "CargoScoopDeployed",
            "CargoScoopRetracted",
            "RememberLimpets",
            "ReceiveText",
            "UnderAttack",
            "ShipTargeted",
            "BountyScanned",
            "CombatEntered",
            "CombatExited",
            "ShieldState",
            "HullDamage",
            "HeatWarning",
            "HeatDamage",
            "FsdMassLockEscaped",
        },
        allowed_status_events={
            "InDanger",
            "OutofDanger",
            "LowFuelWarning",
            "LowFuelWarningCleared",
            "CargoScoopDeployed",
            "CargoScoopRetracted",
            "FsdMassLockEscaped",
        },
        allowed_target_legal_statuses={"Enemy", "Wanted", "Hostile"},
        max_events_per_name={
            "ProspectedAsteroid": 2,
            "MiningRefined": 3,
            "LaunchDrone": 2,
            "Cargo": 2,
            "EjectCargo": 2,
            "CollectCargo": 2,
            "ReceiveText": 6,
            "CargoScoopDeployed": 1,
            "CargoScoopRetracted": 1,
            "InDanger": 1,
            "OutofDanger": 1,
            "ShipTargeted": 2,
            "BountyScanned": 2,
            "UnderAttack": 2,
        },
        prompt_note=(
            "Focus profile: mining. Reply only about the newest mining fact, cargo/limpet state, "
            "local or NPC chatter, nearby threat, shields, heat, hull, or escape state. "
            "Local, system, and NPC chatter is visible because pirates may announce themselves while mining. "
            "Ignore exploration discoveries, station services, memories, prior assistant replies, broad travel history, and economy noise."
        ),
    ),
    "travel-docking-exploration": FocusProfile(
        name="travel-docking-exploration",
        include_memories=False,
        include_prior_assistant=False,
        include_non_pending_events=False,
        compact_status=True,
        allowed_events={
            "ApproachBody",
            "ApproachSettlement",
            "CarrierJump",
            "CodexEntry",
            "CombatDiscovered",
            "DiscoveryScan",
            "Docked",
            "DockingCancelled",
            "DockingDenied",
            "DockingGranted",
            "DockingRequested",
            "DockingTimeout",
            "FSDJump",
            "FSDTarget",
            "FSSAllBodiesFound",
            "FSSBodySignals",
            "FSSDiscoveryScan",
            "FSSSignalDiscovered",
            "FleetCarrierDiscovered",
            "FuelScoop",
            "GenericDiscovered",
            "HighGravityWarning",
            "HighValueLandmarksBody",
            "HGECandidateFound",
            "InstallationDiscovered",
            "JetConeBoost",
            "Location",
            "MegashipDiscovered",
            "NavBeaconDiscovered",
            "NavBeaconScan",
            "NavRoute",
            "NavRouteClear",
            "OutpostDiscovered",
            "ReceiveText",
            "ReservoirReplenished",
            "ResourceExtractionDiscovered",
            "SAAScanComplete",
            "SAASignalsFound",
            "Scan",
            "StationDiscovered",
            "StartJump",
            "SupercruiseDestinationDrop",
            "SupercruiseEntry",
            "SupercruiseExit",
            "TouristBeaconDiscovered",
            "Undocked",
            "UnknownSignalDiscovered",
        },
        allowed_status_events={
            "FsdCharging",
            "FsdMassLockEscaped",
            "FsdMassLocked",
            "FuelScoopStarted",
            "FuelScoopEnded",
            "GlideModeEntered",
            "GlideModeExited",
            "HighGravityWarning",
            "InDockingRange",
            "LandingGearDown",
            "LandingGearUp",
            "LowFuelWarning",
            "LowFuelWarningCleared",
        },
        max_events_per_name={
            "CombatDiscovered": 4,
            "FSSSignalDiscovered": 8,
            "FleetCarrierDiscovered": 6,
            "GenericDiscovered": 4,
            "InstallationDiscovered": 4,
            "MegashipDiscovered": 3,
            "NavBeaconDiscovered": 2,
            "OutpostDiscovered": 4,
            "ReceiveText": 6,
            "ResourceExtractionDiscovered": 4,
            "StationDiscovered": 4,
            "UnknownSignalDiscovered": 4,
        },
        prompt_note=(
            "Focus profile: travel-docking-exploration. Reply only about the newest route, jump, arrival, "
            "docking, glide/orbital, scan, discovery, fuel, local chatter, or immediate travel safety fact. "
            "Do not attach mining, cargo, market, station-service, combat target churn, memories, or prior assistant replies unless directly relevant."
        ),
    ),
    "commerce": FocusProfile(
        name="commerce",
        include_memories=False,
        include_prior_assistant=False,
        include_non_pending_events=False,
        compact_status=True,
        allowed_events={
            "MarketSell",
            "MarketBuy",
            "BuyDrones",
            "SellDrones",
            "RefuelAll",
            "RepairAll",
            "Repair",
            "RestockVehicle",
            "BuyAmmo",
            "RedeemVoucher",
            "PayFines",
            "PowerplayMerits",
            "PowerplayRank",
            "Cargo",
            "RememberLimpets",
        },
        max_events_per_name={
            "MarketSell": 2,
            "MarketBuy": 2,
            "BuyDrones": 1,
            "SellDrones": 1,
            "RefuelAll": 1,
            "RepairAll": 1,
            "Repair": 1,
            "RestockVehicle": 1,
            "BuyAmmo": 1,
            "RedeemVoucher": 1,
            "PayFines": 1,
            "PowerplayMerits": 1,
            "PowerplayRank": 1,
            "Cargo": 1,
            "RememberLimpets": 1,
        },
        prompt_note=(
            "Focus profile: commerce. Reply only about the newest verified transaction, sale, purchase, "
            "repair, refuel, restock, voucher, fine, merits, rank, or directly resulting cargo state. "
            "For a MarketSell event, lead with what was sold, quantity, and total credits. "
            "If MarketSell appears with refuel, repair, cargo capacity, or limpets reminders in the same batch, "
            "MarketSell is the main subject. "
            "Do not replace a sale with cargo capacity, limpets, station services, memories, or prior assistant replies."
        ),
    ),
    "quiet": FocusProfile(
        name="quiet",
        include_memories=False,
        include_prior_assistant=False,
        include_non_pending_events=False,
        compact_status=True,
        allowed_events={
            "UnderAttack",
            "ShieldState",
            "HullDamage",
            "HeatWarning",
            "HeatDamage",
            "CockpitBreached",
            "Died",
            "DockingGranted",
            "DockingDenied",
            "Docked",
            "Undocked",
            "FSDJump",
            "StartJump",
            "SupercruiseEntry",
            "SupercruiseExit",
            "MarketSell",
            "MarketBuy",
        },
        allowed_status_events={
            "FsdCharging",
            "FsdMassLockEscaped",
            "LowFuelWarning",
            "LowHealthWarning",
            "LowOxygenWarning",
        },
        max_events_per_name={
            "UnderAttack": 1,
            "ShieldState": 1,
            "HullDamage": 1,
            "HeatWarning": 1,
            "HeatDamage": 1,
            "DockingGranted": 1,
            "DockingDenied": 1,
            "FSDJump": 1,
            "StartJump": 1,
            "FsdCharging": 1,
        },
        prompt_note=(
            "Focus profile: quiet. Speak only for direct Commander speech, tool results, critical safety facts, "
            "or major verified results. Keep it very short and ignore routine chatter."
        ),
    ),
    "tool-result": FocusProfile(
        name="tool-result",
        include_memories=False,
        include_prior_assistant=False,
        include_non_pending_events=False,
        compact_status=True,
        allowed_events={
            "DockingCancelled",
            "DockingDenied",
            "DockingGranted",
            "DockingRequested",
            "DockingTimeout",
        },
        allowed_status_events={
            "CargoScoopDeployed",
            "CargoScoopRetracted",
            "HardpointsDeployed",
            "HardpointsRetracted",
            "LandingGearDown",
            "LandingGearUp",
            "LightsOff",
            "LightsOn",
            "NightVisionOff",
            "NightVisionOn",
            "SilentRunningOff",
            "SilentRunningOn",
        },
        max_events_per_name={
            "CargoScoopDeployed": 1,
            "CargoScoopRetracted": 1,
            "HardpointsDeployed": 1,
            "HardpointsRetracted": 1,
            "LandingGearDown": 1,
            "LandingGearUp": 1,
            "LightsOff": 1,
            "LightsOn": 1,
            "NightVisionOff": 1,
            "NightVisionOn": 1,
            "SilentRunningOff": 1,
            "SilentRunningOn": 1,
        },
        prompt_note=(
            "Focus profile: tool-result. Reply only about the tool result and its directly verified matching ship event. "
            "If the tool result is a focus-control result from setFocusProfile, switchFocus, or getFocusProfile, "
            "reply only about the focus profile and ignore ship status. "
            "Do not attach carriers, stations, ring contents, mining context, route state, FSD state, memories, or prior assistant replies."
        ),
    ),
}


def _event_content(event: Event) -> dict[str, Any] | None:
    if isinstance(event, (GameEvent, ProjectedEvent, ExternalEvent, QuestEvent)):
        return event.content
    if isinstance(event, StatusEvent):
        return event.status
    return None


def event_name(event: Event) -> str:
    content = _event_content(event)
    if content:
        return str(content.get("event", event.kind))
    return str(getattr(event, "kind", type(event).__name__))


def _best_event_reason_by_priority(
    events: list[Event],
    priority: tuple[str, ...],
) -> str | None:
    """Return the best event reason, preferring higher priority and newer events."""
    priority_index = {name: index for index, name in enumerate(priority)}
    best_name: str | None = None
    best_score: tuple[int, float] | None = None

    for event in events:
        content = _event_content(event)
        if not content:
            continue

        current_event_name = str(content.get("event", ""))
        if current_event_name not in priority_index:
            continue

        processed_at = getattr(event, "processed_at", 0.0) or 0.0
        score = (priority_index[current_event_name], -processed_at)
        if best_score is None or score < best_score:
            best_score = score
            best_name = current_event_name

    return best_name


def resolve_focus_profile(
    projected_states: ProjectedStates,
    pending_events: list[Event],
    manual_profile_name: FocusProfileName = "normal",
) -> EffectiveFocusProfile:
    """Resolve the effective profile for this reply.

    Direct Commander speech and tool flows keep the manual profile so commands and
    questions are not made context-blind by an automatic focus change.
    """
    manual_profile = DEFAULT_FOCUS_PROFILES.get(
        manual_profile_name,
        DEFAULT_FOCUS_PROFILES["normal"],
    )

    has_tool_result = False
    for event in pending_events:
        if isinstance(event, ConversationEvent) and event.kind == "user":
            return EffectiveFocusProfile(manual_profile, "commander speech", False)
        if isinstance(event, ToolEvent):
            has_tool_result = True

    if has_tool_result:
        return EffectiveFocusProfile(
            DEFAULT_FOCUS_PROFILES["tool-result"],
            "tool result",
            True,
        )

    if manual_profile_name == "full-context":
        return EffectiveFocusProfile(manual_profile, "manual full-context", False)

    recent_pending_events = _recent_pending_events(pending_events)

    in_combat = get_state_dict(projected_states, "InCombat")
    if in_combat.get("InCombat", False):
        return EffectiveFocusProfile(
            DEFAULT_FOCUS_PROFILES["combat-focus"],
            "InCombat projection",
            True,
        )

    combat_trigger_events = {
        "CombatEntered",
        "UnderAttack",
        "Bounty",
        "BountyScanned",
        "FactionKillBond",
        "ShieldState",
        "HullDamage",
        "HeatWarning",
        "HeatDamage",
        "Died",
        "CockpitBreached",
        "BeingInterdicted",
        "Interdicted",
    }
    hostile_statuses = DEFAULT_FOCUS_PROFILES["combat-focus"].allowed_target_legal_statuses

    for event in recent_pending_events:
        content = _event_content(event)
        if not content:
            continue

        current_event_name = str(content.get("event", ""))
        if current_event_name in combat_trigger_events:
            return EffectiveFocusProfile(
                DEFAULT_FOCUS_PROFILES["combat-focus"],
                current_event_name,
                True,
            )

        if (
            current_event_name == "ShipTargeted"
            and content.get("LegalStatus") in hostile_statuses
        ):
            return EffectiveFocusProfile(
                DEFAULT_FOCUS_PROFILES["combat-focus"],
                "hostile target",
                True,
            )

    commerce_trigger_events = (
        "MarketSell",
        "MarketBuy",
        "RedeemVoucher",
        "PayFines",
        "PowerplayMerits",
        "PowerplayRank",
        "BuyDrones",
        "SellDrones",
        "RestockVehicle",
        "BuyAmmo",
        "RepairAll",
        "Repair",
        "RefuelAll",
    )

    for trigger_event_name in commerce_trigger_events:
        for event in recent_pending_events:
            content = _event_content(event)
            if not content:
                continue

            current_event_name = str(content.get("event", ""))
            if current_event_name == trigger_event_name:
                return EffectiveFocusProfile(
                    DEFAULT_FOCUS_PROFILES["commerce"],
                    current_event_name,
                    True,
                )

    mining_trigger_events = {
        "ProspectedAsteroid",
        "MiningRefined",
        "LaunchDrone",
        "EjectCargo",
        "CollectCargo",
        "CargoScoopDeployed",
        "CargoScoopRetracted",
        "RememberLimpets",
    }

    for event in recent_pending_events:
        content = _event_content(event)
        if not content:
            continue

        current_event_name = str(content.get("event", ""))
        if current_event_name in mining_trigger_events:
            return EffectiveFocusProfile(
                DEFAULT_FOCUS_PROFILES["mining"],
                current_event_name,
                True,
            )

    travel_trigger_events = {
        "ApproachBody",
        "ApproachSettlement",
        "CarrierJump",
        "CodexEntry",
        "DiscoveryScan",
        "Docked",
        "DockingCancelled",
        "DockingDenied",
        "DockingGranted",
        "DockingRequested",
        "DockingTimeout",
        "FSDJump",
        "FSDTarget",
        "FSSAllBodiesFound",
        "FSSBodySignals",
        "FSSDiscoveryScan",
        "FSSSignalDiscovered",
        "FuelScoop",
        "HighGravityWarning",
        "HighValueLandmarksBody",
        "HGECandidateFound",
        "JetConeBoost",
        "Location",
        "NavBeaconScan",
        "NavRoute",
        "NavRouteClear",
        "ReservoirReplenished",
        "SAAScanComplete",
        "SAASignalsFound",
        "Scan",
        "StartJump",
        "SupercruiseDestinationDrop",
        "SupercruiseEntry",
        "SupercruiseExit",
        "Undocked",
    }
    travel_status_events = {
        "FsdCharging",
        "FsdMassLockEscaped",
        "FsdMassLocked",
        "FuelScoopStarted",
        "FuelScoopEnded",
        "GlideModeEntered",
        "GlideModeExited",
        "HighGravityWarning",
        "InDockingRange",
        "LandingGearDown",
        "LandingGearUp",
        "LowFuelWarning",
        "LowFuelWarningCleared",
    }

    travel_reason = _best_event_reason_by_priority(
        recent_pending_events,
        (
            "FSDJump",
            "SupercruiseDestinationDrop",
            "SupercruiseExit",
            "DockingGranted",
            "Docked",
            "DockingDenied",
            "DockingTimeout",
            "Undocked",
            "CarrierJump",
            "JetConeBoost",
            "HighGravityWarning",
            "FsdMassLockEscaped",
            "LowFuelWarning",
            "FsdCharging",
            "StartJump",
            "FuelScoop",
            "FuelScoopStarted",
            "FuelScoopEnded",
            "FSDTarget",
            "NavRoute",
            "NavRouteClear",
            "ReservoirReplenished",
            "DiscoveryScan",
            "FSSDiscoveryScan",
            "FSSSignalDiscovered",
            "FSSAllBodiesFound",
            "FSSBodySignals",
            "SAAScanComplete",
            "SAASignalsFound",
            "Scan",
            "Location",
            "SupercruiseEntry",
            "DockingRequested",
            "DockingCancelled",
            "ApproachBody",
            "ApproachSettlement",
            "CodexEntry",
            "HighValueLandmarksBody",
            "HGECandidateFound",
            "NavBeaconScan",
        ),
    )
    if travel_reason:
        return EffectiveFocusProfile(
            DEFAULT_FOCUS_PROFILES["travel-docking-exploration"],
            travel_reason,
            True,
        )

    for event in recent_pending_events:
        content = _event_content(event)
        if not content:
            continue

        current_event_name = str(content.get("event", ""))
        if current_event_name in travel_trigger_events or current_event_name in travel_status_events:
            return EffectiveFocusProfile(
                DEFAULT_FOCUS_PROFILES["travel-docking-exploration"],
                current_event_name,
                True,
            )

    return EffectiveFocusProfile(manual_profile, "manual/default", False)


def _recent_pending_events(pending_events: list[Event], window_seconds: float = 30.0) -> list[Event]:
    """Return the newest pending cluster for automatic profile selection."""
    if not pending_events:
        return []

    latest_processed_at = max(
        (getattr(event, "processed_at", 0.0) or 0.0)
        for event in pending_events
    )
    if latest_processed_at <= 0:
        return pending_events[-25:]

    return [
        event
        for event in pending_events
        if latest_processed_at - (getattr(event, "processed_at", 0.0) or 0.0) <= window_seconds
    ]


def should_include_event(
    event: Event,
    effective_profile: EffectiveFocusProfile,
    is_pending: bool,
) -> bool:
    profile = effective_profile.profile
    if profile.name == "normal":
        return True

    if isinstance(event, ConversationEvent):
        if profile.name == "tool-result":
            return is_pending
        if event.kind == "user":
            return is_pending
        if event.kind == "assistant":
            return profile.include_prior_assistant
        return is_pending

    if isinstance(event, ToolEvent):
        return is_pending or profile.include_non_pending_events

    if isinstance(event, MemoryEvent):
        return profile.include_memories

    content = _event_content(event)
    if not content:
        return False

    if not is_pending and not profile.include_non_pending_events:
        return False

    current_event_name = str(content.get("event", ""))

    if isinstance(event, StatusEvent):
        return current_event_name in profile.allowed_status_events

    if current_event_name not in profile.allowed_events:
        return False

    if current_event_name == "ShipTargeted":
        return content.get("LegalStatus") in profile.allowed_target_legal_statuses

    return True


def _clean_target_info(target_info: dict[str, Any]) -> dict[str, Any]:
    if not target_info:
        return {}

    clean: dict[str, Any] = {}
    pilot_name = target_info.get("PilotName_Localised") or target_info.get("PilotName")
    ship_name = target_info.get("Ship_Localised") or target_info.get("Target_Localised") or target_info.get("Ship")

    if isinstance(pilot_name, str) and "$" not in pilot_name and "#index=" not in pilot_name:
        clean["PilotName"] = pilot_name
    if isinstance(ship_name, str) and "$" not in ship_name and "#index=" not in ship_name:
        clean["Ship"] = ship_name

    for key in (
        "LegalStatus",
        "Bounty",
        "ShieldHealth",
        "HullHealth",
        "Faction",
        "PilotRank",
        "TargetLocked",
    ):
        value = target_info.get(key)
        if value not in (None, "", []):
            clean[key] = value

    return clean


def compact_combat_status(projected_states: ProjectedStates) -> dict[str, Any]:
    current_status = get_state_dict(projected_states, "CurrentStatus")
    flags = current_status.get("flags", {}) if isinstance(current_status, dict) else {}
    flags2 = current_status.get("flags2", {}) if isinstance(current_status, dict) else {}
    target_info = get_state_dict(projected_states, "Target")
    in_combat = get_state_dict(projected_states, "InCombat")

    return {
        "InCombat": in_combat.get("InCombat", False),
        "CommanderShip": {
            "ShieldsUp": flags.get("ShieldsUp"),
            "OverHeating": flags.get("OverHeating"),
            "InDanger": flags.get("InDanger"),
            "HardpointsDeployed": flags.get("HardpointsDeployed"),
            "FsdCharging": flags.get("FsdCharging"),
            "FsdMassLocked": flags.get("FsdMassLocked"),
            "FsdCooldown": flags.get("FsdCooldown"),
            "Supercruise": flags.get("Supercruise"),
            "Pips": current_status.get("Pips"),
            "Health": current_status.get("Health"),
            "Oxygen": current_status.get("Oxygen"),
        },
        "CommanderOnFoot": {
            "OnFoot": flags2.get("OnFoot") if isinstance(flags2, dict) else None,
            "LowHealth": flags2.get("LowHealth") if isinstance(flags2, dict) else None,
            "LowOxygen": flags2.get("LowOxygen") if isinstance(flags2, dict) else None,
        },
        "CurrentTarget": _clean_target_info(target_info),
    }


def compact_mining_status(projected_states: ProjectedStates) -> dict[str, Any]:
    current_status = get_state_dict(projected_states, "CurrentStatus")
    flags = current_status.get("flags", {}) if isinstance(current_status, dict) else {}
    cargo_info = get_state_dict(projected_states, "Cargo")
    ship_info = get_state_dict(projected_states, "ShipInfo")
    target_info = get_state_dict(projected_states, "Target")

    cargo_contents: list[str] = []
    for item in cargo_info.get("Inventory", []) if isinstance(cargo_info, dict) else []:
        if not isinstance(item, dict):
            continue
        name = item.get("Name_Localised") or item.get("Name") or "Unknown"
        count = item.get("Count", 0)
        cargo_contents.append(f"{count} x {name}")

    return {
        "MiningStatus": {
            "Cargo": current_status.get("Cargo") or ship_info.get("Cargo"),
            "CargoCapacity": cargo_info.get("Capacity") or ship_info.get("CargoCapacity"),
            "CargoContents": cargo_contents,
            "HasLimpetControllers": ship_info.get("hasLimpets"),
        },
        "CommanderShip": {
            "ShieldsUp": flags.get("ShieldsUp"),
            "OverHeating": flags.get("OverHeating"),
            "InDanger": flags.get("InDanger"),
            "HardpointsDeployed": flags.get("HardpointsDeployed"),
            "FsdMassLocked": flags.get("FsdMassLocked"),
            "CargoScoopDeployed": flags.get("CargoScoopDeployed"),
            "Pips": current_status.get("Pips"),
            "Health": current_status.get("Health"),
        },
        "CurrentTarget": _clean_target_info(target_info),
    }


def _model_or_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _fuel_part(current: Any, capacity: Any) -> dict[str, Any]:
    if current is None:
        return {}

    part: dict[str, Any] = {"CurrentTons": current}
    if capacity not in (None, 0, 0.0, ""):
        part["CapacityTons"] = capacity
        try:
            percent = (float(current) / float(capacity)) * 100
            part["PercentFull"] = round(percent, 1)
            part["Display"] = f"{float(current):.3f} / {float(capacity):.3f} tons ({round(percent, 1)}%)"
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    return part


def format_fuel_status(current_status: dict[str, Any], ship_info: dict[str, Any]) -> dict[str, Any]:
    fuel = current_status.get("Fuel") if isinstance(current_status, dict) else None
    if not isinstance(fuel, dict):
        return {}

    main_current = fuel.get("FuelMain")
    reservoir_current = fuel.get("FuelReservoir")
    main_capacity = ship_info.get("FuelMainCapacity") if isinstance(ship_info, dict) else None
    reservoir_capacity = ship_info.get("FuelReservoirCapacity") if isinstance(ship_info, dict) else None

    fuel_status: dict[str, Any] = {}
    main = _fuel_part(main_current, main_capacity)
    reservoir = _fuel_part(reservoir_current, reservoir_capacity)
    if main:
        fuel_status["MainTank"] = main
    if reservoir:
        fuel_status["Reservoir"] = reservoir

    if main_current is not None and reservoir_current is not None:
        try:
            total_current = float(main_current) + float(reservoir_current)
            total: dict[str, Any] = {"CurrentTons": round(total_current, 3)}
            if main_capacity not in (None, 0, 0.0, "") and reservoir_capacity not in (None, 0, 0.0, ""):
                total_capacity = float(main_capacity) + float(reservoir_capacity)
                percent = (total_current / total_capacity) * 100
                total["CapacityTons"] = round(total_capacity, 3)
                total["PercentFull"] = round(percent, 1)
                total["Display"] = f"{total_current:.3f} / {total_capacity:.3f} tons ({round(percent, 1)}%)"
            fuel_status["TotalFuel"] = total
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    return fuel_status


def compact_travel_status(projected_states: ProjectedStates) -> dict[str, Any]:
    current_status = get_state_dict(projected_states, "CurrentStatus")
    flags = current_status.get("flags", {}) if isinstance(current_status, dict) else {}
    location_info = get_state_dict(projected_states, "Location")
    nav_info = get_state_dict(projected_states, "NavInfo")
    ship_info = get_state_dict(projected_states, "ShipInfo")

    location_keys = (
        "StarSystem",
        "StationName",
        "Station",
        "StationType",
        "Body",
        "BodyType",
        "Docked",
        "Taxi",
        "Multicrew",
        "OnFoot",
        "Latitude",
        "Longitude",
    )
    location = {
        key: location_info.get(key)
        for key in location_keys
        if isinstance(location_info, dict) and location_info.get(key) not in (None, "", [])
    }

    route_entries = nav_info.get("NavRoute", []) if isinstance(nav_info, dict) else []
    route: dict[str, Any] = {}
    if route_entries:
        first = _model_or_dict(route_entries[0])
        last = _model_or_dict(route_entries[-1])
        route = {
            "JumpsRemaining": max(len(route_entries) - 1, 0),
            "NextSystem": first.get("StarSystem"),
            "DestinationSystem": last.get("StarSystem"),
        }
    next_target = nav_info.get("NextJumpTarget") if isinstance(nav_info, dict) else None
    if next_target:
        target = _model_or_dict(next_target)
        if target.get("StarSystem"):
            route["NextJumpTarget"] = target.get("StarSystem")

    fuel_status = format_fuel_status(current_status, ship_info)

    return {
        "TravelStatus": {
            "Location": location,
            "Route": route,
        },
        "CommanderShip": {
            "Ship": ship_info.get("ShipType") or ship_info.get("ShipType_Localised"),
            "ShieldsUp": flags.get("ShieldsUp"),
            "OverHeating": flags.get("OverHeating"),
            "InDanger": flags.get("InDanger"),
            "FsdCharging": flags.get("FsdCharging"),
            "FsdMassLocked": flags.get("FsdMassLocked"),
            "FsdCooldown": flags.get("FsdCooldown"),
            "Supercruise": flags.get("Supercruise"),
            "Docked": flags.get("Docked"),
            "LandingGearDown": flags.get("LandingGearDown"),
            "FuelScoop": flags.get("FuelScoop"),
            "CargoScoopDeployed": flags.get("CargoScoopDeployed"),
            "Pips": current_status.get("Pips"),
            "Fuel": fuel_status or None,
        },
    }


def compact_tool_status(projected_states: ProjectedStates) -> dict[str, Any]:
    current_status = get_state_dict(projected_states, "CurrentStatus")
    flags = current_status.get("flags", {}) if isinstance(current_status, dict) else {}
    flags2 = current_status.get("flags2", {}) if isinstance(current_status, dict) else {}
    location_info = get_state_dict(projected_states, "Location")
    ship_info = get_state_dict(projected_states, "ShipInfo")
    location_keys = (
        "StarSystem",
        "StationName",
        "Station",
        "StationType",
        "Body",
        "BodyType",
        "Docked",
        "Landed",
    )
    location = {
        key: location_info.get(key)
        for key in location_keys
        if isinstance(location_info, dict) and location_info.get(key) not in (None, "", [])
    }

    return {
        "ToolRelevantShipState": {
            "Docked": flags.get("Docked"),
            "Landed": flags.get("Landed"),
            "LandingGearDown": flags.get("LandingGearDown"),
            "HardpointsDeployed": flags.get("HardpointsDeployed"),
            "CargoScoopDeployed": flags.get("CargoScoopDeployed"),
            "LightsOn": flags.get("LightsOn"),
            "SilentRunning": flags.get("SilentRunning"),
            "NightVision": flags.get("NightVision"),
            "GuiFocus": current_status.get("GuiFocus") if isinstance(current_status, dict) else None,
            "OnFoot": flags2.get("OnFoot") if isinstance(flags2, dict) else None,
            "Destination": current_status.get("Destination") if isinstance(current_status, dict) else None,
            "Location": location or None,
            "Fuel": format_fuel_status(current_status, ship_info) or None,
        }
    }
