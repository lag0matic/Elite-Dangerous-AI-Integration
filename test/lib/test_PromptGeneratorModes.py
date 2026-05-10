from src.lib.Event import GameEvent, MemoryEvent
from src.lib.PromptGenerator import PromptGenerator


class DummySystemDatabase:
    pass


class MinimalPromptGenerator(PromptGenerator):
    def generate_status_message(self, projected_states, search_agent_context=False):
        return "# Main ship status\nbalance: 1000\n\n# Stations in local system\nBig Station: {}\n"


def _generator() -> MinimalPromptGenerator:
    return MinimalPromptGenerator(
        commander_name="Dark",
        character_prompt="Cassia test prompt for {commander_name}.",
        important_game_events=[],
        system_db=DummySystemDatabase(),
    )


def _game_event() -> GameEvent:
    return GameEvent(
        content={"event": "FsdCharging", "timestamp": "2026-05-10T00:00:00+00:00"},
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )


def _memory() -> MemoryEvent:
    return MemoryEvent(
        content="Dark sold platinum and docked at Elvstrom Terminal.",
        metadata={"time_until": 1778371200.0},
        embedding=[],
    )


def _prompt_text(prompt: list[dict[str, str]]) -> str:
    return "\n".join(str(piece.get("content", "")) for piece in prompt)


def test_automatic_telemetry_prompt_does_not_include_long_term_memories():
    event = _game_event()

    prompt, usage = _generator().generate_prompt(
        events=[event],
        projected_states={},
        pending_events=[event],
        memories=[_memory()],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "[Ship logbook" not in prompt_text
    assert "Dark sold platinum" not in prompt_text
    assert usage.memory_chars == 0


def test_user_command_prompt_still_includes_long_term_memories():
    event = _game_event()

    prompt, usage = _generator().generate_prompt(
        events=[event],
        projected_states={},
        pending_events=[event],
        memories=[_memory()],
        mode="user_command",
    )

    prompt_text = _prompt_text(prompt)
    assert "[Ship logbook" in prompt_text
    assert "Dark sold platinum" in prompt_text
    assert usage.memory_chars > 0


def test_automatic_telemetry_prompt_uses_core_status_instead_of_full_status():
    event = _game_event()

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {
                "flags": {"InMainShip": True, "Supercruise": True},
                "flags2": {},
                "Cargo": 74,
                "LegalState": "Clean",
            },
            "Location": {"StarSystem": "HIP 103687", "Docked": False},
            "ShipInfo": {"Name": "Kestrel", "Type": "cobramkiii", "CargoCapacity": 128},
            "Cargo": {"Capacity": 128},
            "NavInfo": {"NextJumpTarget": "Lave", "NavRoute": [{"StarSystem": "Lave"}]},
            "InCombat": {"InCombat": False},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Core status" in prompt_text
    assert "# Main ship status" not in prompt_text
    assert "# Stations in local system" not in prompt_text
    assert "HIP 103687" in prompt_text
    assert "Supercruise" in prompt_text


def test_user_command_prompt_keeps_full_status_for_now():
    event = _game_event()

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={},
        pending_events=[event],
        memories=[],
        mode="user_command",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Main ship status" in prompt_text
    assert "# Stations in local system" in prompt_text
    assert "# Core status" not in prompt_text


def test_automatic_mining_prompt_includes_all_prospector_materials():
    event = GameEvent(
        content={
            "event": "ProspectedAsteroid",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "Content": "Low",
            "Content_Localised": "Low",
            "Remaining": 100.0,
            "Materials": [
                {"Name": "Gallite", "Proportion": 20.0},
                {"Name": "Praseodymium", "Proportion": 10.52},
                {"Name": "Samarium", "Proportion": 13.07},
            ],
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {
                "flags": {"InMainShip": True, "CargoScoopDeployed": True, "HardpointsDeployed": True},
                "flags2": {},
                "Cargo": 75,
            },
            "Location": {
                "StarSystem": "HIP 103687",
                "PlanetaryRing": "HIP 103687 4 A Ring",
            },
            "ShipInfo": {
                "Name": "Kestrel",
                "Type": "cobramkiii",
                "CargoCapacity": 128,
                "IsMiningShip": True,
                "hasLimpets": True,
            },
            "Cargo": {
                "Capacity": 128,
                "Inventory": [
                    {"Name": "Platinum", "Count": 75},
                    {"Name": "Limpet", "Count": 57},
                ],
            },
            "NavInfo": {},
            "InCombat": {"InCombat": False},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Mining context" in prompt_text
    assert "material_content: Low" in prompt_text
    assert "minerals_remaining_percent: 100.0" in prompt_text
    assert "Gallite" in prompt_text
    assert "Praseodymium" in prompt_text
    assert "Samarium" in prompt_text
    assert "HIP 103687 4 A Ring" in prompt_text
    assert "Platinum" in prompt_text
    assert "Limpet" in prompt_text


def test_non_mining_automatic_prompt_does_not_include_mining_context():
    event = _game_event()

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={},
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Mining context" not in prompt_text
    assert "# Station context" not in prompt_text


def test_automatic_station_prompt_includes_verified_docking_context_and_pad_orientation():
    event = GameEvent(
        content={
            "event": "DockingGranted",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "StationName": "Elvstrom Terminal",
            "StationType": "Coriolis",
            "MarketID": 123,
            "LandingPad": 14,
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {
                "flags": {
                    "InMainShip": True,
                    "FsdMassLocked": True,
                    "LandingGearDown": False,
                },
                "flags2": {},
            },
            "Location": {
                "StarSystem": "HIP 103687",
                "Station": "Elvstrom Terminal",
                "Docked": False,
            },
            "ShipInfo": {},
            "Cargo": {},
            "NavInfo": {},
            "InCombat": {"InCombat": False},
            "DockingEvents": {
                "StationType": "Coriolis",
                "LastEventType": "DockingGranted",
                "DockingComputerState": "auto-docking",
            },
            "InDockingRange": {
                "ReceivedFsdMassLocked": True,
                "ReceivedNoFireZoneEntered": True,
            },
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Station context" in prompt_text
    assert "Elvstrom Terminal" in prompt_text
    assert "landing_pad: 14" in prompt_text
    assert "9 o'clock, back" in prompt_text
    assert "green on right" in prompt_text
    assert "no_fire_zone_entered: true" in prompt_text
    assert "docking_computer: auto-docking" in prompt_text
    assert "# Stations in local system" not in prompt_text


def test_automatic_docking_requested_prompt_includes_available_pad_counts():
    event = GameEvent(
        content={
            "event": "DockingRequested",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "StationName": "V4N-NVK",
            "StationType": "FleetCarrier",
            "MarketID": 456,
            "LandingPads": {"Small": 4, "Medium": 4, "Large": 8},
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {"flags": {"InMainShip": True}, "flags2": {}},
            "Location": {"StarSystem": "Scorpii Sector GR-W c1-29", "Station": "V4N-NVK"},
            "ShipInfo": {},
            "Cargo": {},
            "NavInfo": {},
            "InCombat": {"InCombat": False},
            "DockingEvents": {
                "StationType": "FleetCarrier",
                "LastEventType": "DockingRequested",
                "DockingComputerState": "deactivated",
            },
            "InDockingRange": {},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Station context" in prompt_text
    assert "available_landing_pads" in prompt_text
    assert "Small: 4" in prompt_text
    assert "Medium: 4" in prompt_text
    assert "Large: 8" in prompt_text


def test_automatic_ship_prompt_includes_verified_fsd_state_not_route_inference():
    event = GameEvent(
        content={"event": "FSDTarget", "timestamp": "2026-05-10T00:00:00+00:00", "Name": "Lave"},
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {
                "flags": {
                    "InMainShip": True,
                    "Docked": False,
                    "FsdMassLocked": True,
                    "FsdCharging": False,
                    "Supercruise": False,
                },
                "flags2": {},
                "Cargo": 75,
                "Destination": {"Name": "Lave"},
            },
            "Location": {"StarSystem": "Scorpii Sector GR-W c1-29", "Station": "V4N-NVK"},
            "ShipInfo": {"Name": "Kestrel", "Type": "cobramkiii", "ShipIdent": "DA-07E", "CargoCapacity": 128},
            "Cargo": {},
            "NavInfo": {"NextJumpTarget": "Lave", "NavRoute": [{"StarSystem": "Lave"}]},
            "InCombat": {"InCombat": False},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Ship context" in prompt_text
    assert "fsd_mass_locked: true" in prompt_text
    assert "fsd_charging: false" in prompt_text
    assert "supercruise: false" in prompt_text
    assert "destination_from_status: Lave" in prompt_text
    assert "Route target and destination are context only" in prompt_text


def test_automatic_ship_prompt_supercruise_exit_does_not_imply_fsd_charging():
    event = GameEvent(
        content={
            "event": "SupercruiseExit",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "StarSystem": "HIP 103687",
            "Body": "Elvstrom Terminal",
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {
                "flags": {
                    "InMainShip": True,
                    "Supercruise": False,
                    "FsdCharging": False,
                    "FsdMassLocked": False,
                },
                "flags2": {},
            },
            "Location": {"StarSystem": "HIP 103687"},
            "ShipInfo": {"Name": "Kestrel", "Type": "cobramkiii"},
            "Cargo": {},
            "NavInfo": {"NextJumpTarget": "Unknown", "NavRoute": []},
            "InCombat": {"InCombat": False},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Ship context" in prompt_text
    assert "event: SupercruiseExit" in prompt_text
    assert "supercruise: false" in prompt_text
    assert "fsd_charging: false" in prompt_text
    assert "fsd_mass_locked: false" in prompt_text


def test_automatic_combat_prompt_includes_target_and_bounty_context():
    event = GameEvent(
        content={
            "event": "ShipTargeted",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "TargetLocked": True,
            "PilotName_Localised": "Some Bastard",
            "Ship_Localised": "Fer-de-Lance",
            "LegalStatus": "Wanted",
            "Bounty": 500000,
            "ShieldHealth": 87.5,
            "HullHealth": 100.0,
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {
                "flags": {"InMainShip": True, "ShieldsUp": True, "HardpointsDeployed": True, "InDanger": True},
                "flags2": {},
                "Pips": {"system": 2, "engine": 2, "weapons": 2},
                "LegalState": "Clean",
            },
            "Location": {"StarSystem": "Lave"},
            "ShipInfo": {"Name": "Kestrel", "Type": "cobramkiii"},
            "Cargo": {},
            "NavInfo": {},
            "InCombat": {"InCombat": True},
            "Loadout": {"HullHealth": 0.92},
            "Target": {
                "PilotName": "Some Bastard",
                "Ship": "Fer-de-Lance",
                "ScanStage": 3,
                "LegalStatus": "Wanted",
                "Bounty": 500000,
                "ShieldHealth": 87.5,
                "HullHealth": 100.0,
            },
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Combat context" in prompt_text
    assert "Some Bastard" in prompt_text
    assert "Fer-de-Lance" in prompt_text
    assert "legal_status: Wanted" in prompt_text
    assert "bounty: 500000" in prompt_text
    assert "shields_up: true" in prompt_text
    assert "hardpoints_deployed: true" in prompt_text
    assert "# Mining context" not in prompt_text
    assert "# Station context" not in prompt_text


def test_automatic_combat_prompt_includes_shield_state_without_unrelated_context():
    event = GameEvent(
        content={
            "event": "ShieldState",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "ShieldsUp": False,
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {
                "flags": {"InMainShip": True, "ShieldsUp": False, "InDanger": True},
                "flags2": {},
            },
            "Location": {"StarSystem": "Lave"},
            "ShipInfo": {"Name": "Kestrel", "Type": "cobramkiii"},
            "Cargo": {},
            "NavInfo": {"NextJumpTarget": "Distraction", "NavRoute": [{"StarSystem": "Distraction"}]},
            "InCombat": {"InCombat": True},
            "Loadout": {"HullHealth": 0.64},
            "Target": {},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Combat context" in prompt_text
    assert "shields_up: false" in prompt_text
    assert "hull_health: 0.64" in prompt_text
    assert "in_danger: true" in prompt_text
    assert "# Ship context" not in prompt_text
    assert "# Stations in local system" not in prompt_text


def test_automatic_exploration_prompt_includes_hge_context_without_system_encyclopedia():
    event = GameEvent(
        content={
            "event": "HGECandidateFound",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "StarSystem": "LAWD 96",
            "SystemAddress": 12345,
            "SystemAllegiance": "Federation",
            "Population": 3368591,
            "HGECandidateMaterials": ["Core Dynamics Composites", "Proto Heat Radiators"],
            "HGEMatchedStates": ["boom"],
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {"flags": {"InMainShip": True}, "flags2": {}},
            "Location": {"StarSystem": "LAWD 96", "Star": "LAWD 96"},
            "ShipInfo": {},
            "Cargo": {},
            "NavInfo": {"NextJumpTarget": "Chona", "NavRoute": [{"StarSystem": "Chona"}]},
            "InCombat": {"InCombat": False},
            "FSSSignals": {
                "SystemAddress": 12345,
                "FleetCarrier": ["Carrier One", "Carrier Two"],
                "Station": ["Holden Dock"],
                "Megaship": [],
            },
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Exploration context" in prompt_text
    assert "LAWD 96" in prompt_text
    assert "Core Dynamics Composites" in prompt_text
    assert "Proto Heat Radiators" in prompt_text
    assert "hge_matched_states" in prompt_text
    assert "FleetCarrier: 2" in prompt_text
    assert "Station: 1" in prompt_text
    assert "# Stations in local system" not in prompt_text
    assert "# Bodies in local system" not in prompt_text
    assert "# Local system" not in prompt_text


def test_automatic_exploration_prompt_includes_body_signal_counts_and_genuses():
    event = GameEvent(
        content={
            "event": "SAASignalsFound",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "BodyName": "HIP 103687 4 a",
            "BodyID": 12,
            "SystemAddress": 12345,
            "Signals": [
                {"Type": "$SAA_SignalType_Biological;", "Type_Localised": "Biological", "Count": 3},
                {"Type": "$SAA_SignalType_Geological;", "Type_Localised": "Geological", "Count": 9},
            ],
            "Genuses": [
                {"Genus": "$Codex_Ent_Brancae_Name;", "Genus_Localised": "Brain Trees"},
            ],
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {"flags": {"InMainShip": True}, "flags2": {}},
            "Location": {"StarSystem": "HIP 103687", "Planet": "HIP 103687 4 a"},
            "ShipInfo": {},
            "Cargo": {},
            "NavInfo": {},
            "InCombat": {"InCombat": False},
            "FSSSignals": {},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Exploration context" in prompt_text
    assert "HIP 103687 4 a" in prompt_text
    assert "Biological" in prompt_text
    assert "Geological" in prompt_text
    assert "Brain Trees" in prompt_text


def test_automatic_social_prompt_uses_friend_context_not_previous_activity():
    event = GameEvent(
        content={
            "event": "Friends",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "Name": "RatherRude",
            "Status": "Online",
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {"flags": {"InMainShip": True}, "flags2": {}, "Cargo": 75},
            "Location": {"StarSystem": "HIP 103687", "PlanetaryRing": "HIP 103687 4 A Ring"},
            "ShipInfo": {"IsMiningShip": True},
            "Cargo": {"Inventory": [{"Name": "Platinum", "Count": 75}]},
            "NavInfo": {},
            "InCombat": {"InCombat": False},
            "Friends": {"Online": ["RatherRude"], "Pending": []},
            "Wing": {"Members": []},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Social context" in prompt_text
    assert "RatherRude" in prompt_text
    assert "status: Online" in prompt_text
    assert "online_count: 1" in prompt_text
    assert "# Mining context" not in prompt_text
    assert "# Ship context" not in prompt_text


def test_automatic_social_prompt_includes_comms_message_and_wing_members():
    event = GameEvent(
        content={
            "event": "ReceiveText",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "From": "Traffic Control",
            "Channel": "npc",
            "Message": "No fire zone entered.",
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {"flags": {"InMainShip": True}, "flags2": {}},
            "Location": {"StarSystem": "Lave"},
            "ShipInfo": {},
            "Cargo": {},
            "NavInfo": {},
            "InCombat": {"InCombat": False},
            "Friends": {"Online": ["RatherRude", "Cobra_Phenix"], "Pending": ["NewPilot"]},
            "Wing": {"Members": ["RatherRude"]},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Social context" in prompt_text
    assert "Traffic Control" in prompt_text
    assert "channel: npc" in prompt_text
    assert "No fire zone entered." in prompt_text
    assert "Cobra_Phenix" in prompt_text
    assert "NewPilot" in prompt_text
    assert "member_count: 1" in prompt_text


def test_automatic_trading_prompt_separates_transaction_total_from_balance():
    event = GameEvent(
        content={
            "event": "MarketSell",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "Type": "platinum",
            "Type_Localised": "Platinum",
            "Count": 256,
            "SellPrice": 289000,
            "TotalSale": 73984000,
            "AvgPricePaid": 0,
            "MarketID": 123,
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {"flags": {"InMainShip": True}, "flags2": {}, "Cargo": 0, "Balance": 12700000000},
            "Location": {"StarSystem": "HIP 103687", "Station": "Elvstrom Terminal", "Docked": True},
            "ShipInfo": {},
            "Cargo": {"TotalItems": 0, "Capacity": 512, "Inventory": []},
            "NavInfo": {},
            "InCombat": {"InCombat": False},
            "Missions": {"Active": []},
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Trading and missions context" in prompt_text
    assert "commodity: Platinum" in prompt_text
    assert "transaction_total_sale: 73984000" in prompt_text
    assert "current_total_balance: 12700000000" in prompt_text
    assert "Transaction totals are not total credit balance." in prompt_text
    assert "# Stations in local system" not in prompt_text


def test_automatic_mission_prompt_includes_matching_active_mission():
    event = GameEvent(
        content={
            "event": "MissionAccepted",
            "timestamp": "2026-05-10T00:00:00+00:00",
            "MissionID": 42,
            "Name": "Mission_Delivery",
            "LocalisedName": "Deliver the cargo",
            "Faction": "Aisling's Angels",
            "Reward": 1500000,
            "DestinationSystem": "Chona",
            "DestinationStation": "Smoot Station",
            "Influence": "Med",
            "Reputation": "High",
            "Expiry": "2026-05-11T00:00:00Z",
            "Wing": False,
        },
        historic=False,
        processed_at=1.0,
        responded_at=None,
    )

    prompt, _usage = _generator().generate_prompt(
        events=[event],
        projected_states={
            "CurrentStatus": {"flags": {"InMainShip": True}, "flags2": {}, "Balance": 12700000000},
            "Location": {"StarSystem": "Lave", "Station": "Lave Station", "Docked": True},
            "ShipInfo": {},
            "Cargo": {"TotalItems": 10, "Capacity": 32, "Inventory": [{"Name": "Aisling Media Materials", "Count": 10}]},
            "NavInfo": {},
            "InCombat": {"InCombat": False},
            "Missions": {
                "Active": [
                    {
                        "MissionID": 42,
                        "LocalisedName": "Deliver the cargo",
                        "Faction": "Aisling's Angels",
                        "DestinationSystem": "Chona",
                        "DestinationStation": "Smoot Station",
                        "Reward": 1500000,
                    }
                ]
            },
        },
        pending_events=[event],
        memories=[],
        mode="automatic_telemetry",
    )

    prompt_text = _prompt_text(prompt)
    assert "# Trading and missions context" in prompt_text
    assert "Deliver the cargo" in prompt_text
    assert "Aisling's Angels" in prompt_text
    assert "Smoot Station" in prompt_text
    assert "active_count: 1" in prompt_text
    assert "Aisling Media Materials" in prompt_text
