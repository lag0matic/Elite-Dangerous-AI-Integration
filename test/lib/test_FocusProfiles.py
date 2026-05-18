from src.lib.Event import ConversationEvent, GameEvent, ProjectedEvent, StatusEvent
from src.lib.FocusProfiles import (
    DEFAULT_FOCUS_PROFILES,
    EffectiveFocusProfile,
    compact_tool_status,
    compact_travel_status,
    resolve_focus_profile,
    should_include_event,
)


def game_event(name: str, processed_at: float = 1.0, **content: object) -> GameEvent:
    return GameEvent(
        content={
            "event": name,
            "timestamp": "2026-05-17T13:37:00Z",
            **content,
        },
        historic=False,
        processed_at=processed_at,
    )


def status_event(name: str, processed_at: float = 1.0, **status: object) -> StatusEvent:
    return StatusEvent(
        status={
            "event": name,
            **status,
        },
        processed_at=processed_at,
    )


def projected_event(name: str, processed_at: float = 1.0, **content: object) -> ProjectedEvent:
    return ProjectedEvent(
        content={
            "event": name,
            **content,
        },
        processed_at=processed_at,
    )


def test_commerce_focus_outranks_limpet_reminders_when_selling() -> None:
    focus = resolve_focus_profile(
        projected_states={},
        pending_events=[
            game_event("RefuelAll", processed_at=10.0),
            projected_event("RememberLimpets", processed_at=11.0),
            game_event("RepairAll", processed_at=12.0),
            projected_event("RememberLimpets", processed_at=13.0),
            game_event("MarketSell", processed_at=14.0, Type="platinum", Count=60, TotalSale=3415380),
            game_event("PowerplayMerits", processed_at=15.0),
            game_event("Cargo", processed_at=16.0, Count=38),
        ],
    )

    assert focus.profile.name == "commerce"
    assert focus.reason == "MarketSell"


def test_non_pending_user_speech_does_not_leak_into_automatic_focus() -> None:
    focus = EffectiveFocusProfile(
        DEFAULT_FOCUS_PROFILES["travel-docking-exploration"],
        "FsdCharging",
        True,
    )
    old_question = ConversationEvent(
        kind="user",
        content="How's our inventory?",
        processed_at=1.0,
    )
    pending_question = ConversationEvent(
        kind="user",
        content="How's our inventory?",
        processed_at=2.0,
    )

    assert not should_include_event(old_question, focus, is_pending=False)
    assert should_include_event(pending_question, focus, is_pending=True)


def test_travel_compact_status_returns_structured_state_not_null() -> None:
    status = compact_travel_status(
        {
            "CurrentStatus": {
                "flags": {
                    "ShieldsUp": True,
                    "OverHeating": False,
                    "InDanger": False,
                    "FsdCharging": True,
                    "FsdMassLocked": False,
                    "FsdCooldown": False,
                    "Supercruise": False,
                    "Docked": False,
                    "LandingGearDown": False,
                    "CargoScoopDeployed": False,
                },
                "flags2": {},
                "Pips": {"system": 4, "engine": 2, "weapons": 0},
                "Fuel": {"FuelMain": 31.1, "FuelReservoir": 0.6},
            },
            "Location": {"StarSystem": "HIP 103687"},
            "NavInfo": {},
            "ShipInfo": {"FuelMainCapacity": 32, "FuelReservoirCapacity": 0.6},
        }
    )

    assert status["TravelStatus"]["Location"]["StarSystem"] == "HIP 103687"
    assert status["CommanderShip"]["FsdCharging"] is True
    assert status["CommanderShip"]["Fuel"]["MainTank"]["CurrentTons"] == 31.1
    assert status["CommanderShip"]["Fuel"]["MainTank"]["CapacityTons"] == 32
    assert status["CommanderShip"]["Fuel"]["MainTank"]["PercentFull"] == 97.2
    assert status["CommanderShip"]["Fuel"]["Reservoir"]["Display"] == "0.600 / 0.600 tons (100.0%)"


def test_tool_compact_status_includes_destination_location_and_semantic_fuel() -> None:
    status = compact_tool_status(
        {
            "CurrentStatus": {
                "flags": {
                    "Docked": False,
                    "Landed": False,
                    "LandingGearDown": True,
                    "HardpointsDeployed": False,
                    "CargoScoopDeployed": False,
                    "LightsOn": False,
                    "SilentRunning": False,
                    "NightVision": False,
                },
                "flags2": {},
                "GuiFocus": "NoFocus",
                "Destination": {
                    "System": 1733119873778,
                    "Body": 1,
                    "Name": "catgirl Air power V4N-NVK",
                },
                "Fuel": {"FuelMain": 31.4, "FuelReservoir": 0.458557},
            },
            "Location": {
                "StarSystem": "HIP 103687",
                "Station": "V4N-NVK",
                "StationType": "FleetCarrier",
            },
            "ShipInfo": {"FuelMainCapacity": 32, "FuelReservoirCapacity": 0.6},
        }
    )

    tool_state = status["ToolRelevantShipState"]
    assert tool_state["Destination"]["Name"] == "catgirl Air power V4N-NVK"
    assert tool_state["Location"]["StationType"] == "FleetCarrier"
    assert tool_state["Fuel"]["Reservoir"]["CurrentTons"] == 0.458557
    assert tool_state["Fuel"]["Reservoir"]["PercentFull"] == 76.4


def test_shield_damage_still_selects_combat_focus_for_safety() -> None:
    focus = resolve_focus_profile(
        projected_states={},
        pending_events=[
            game_event("ShieldState", processed_at=1.0, ShieldsUp=False),
            game_event("HullDamage", processed_at=2.0, Health=0.135897, PlayerPilot=True),
        ],
    )

    assert focus.profile.name == "combat-focus"
    assert focus.reason == "ShieldState"


def test_manual_full_context_bypasses_automatic_mining_focus() -> None:
    focus = resolve_focus_profile(
        projected_states={},
        pending_events=[
            game_event("ProspectedAsteroid", processed_at=1.0),
        ],
        manual_profile_name="full-context",
    )

    assert focus.profile.name == "full-context"
    assert focus.reason == "manual full-context"


def test_reservoir_replenished_selects_travel_not_mining() -> None:
    focus = resolve_focus_profile(
        projected_states={},
        pending_events=[
            game_event(
                "ReservoirReplenished",
                processed_at=1.0,
                FuelMain=88.447075,
                FuelReservoir=1.14,
            ),
        ],
        manual_profile_name="travel-docking-exploration",
    )

    assert focus.profile.name == "travel-docking-exploration"
    assert focus.reason == "ReservoirReplenished"


def test_mining_focus_does_not_include_reservoir_replenished_by_default() -> None:
    focus = EffectiveFocusProfile(
        DEFAULT_FOCUS_PROFILES["mining"],
        "manual/default",
        False,
    )

    assert not should_include_event(
        game_event("ReservoirReplenished"),
        focus,
        is_pending=True,
    )


def test_direct_commander_speech_uses_manual_focus() -> None:
    focus = resolve_focus_profile(
        projected_states={},
        pending_events=[
            ConversationEvent(kind="user", content="Go quiet.", processed_at=1.0),
        ],
        manual_profile_name="quiet",
    )

    assert focus.profile.name == "quiet"
    assert focus.reason == "commander speech"
