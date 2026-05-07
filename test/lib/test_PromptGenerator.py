import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from lib.PromptGenerator import PromptGenerator
from lib.Event import ConversationEvent, GameEvent


class FakeSystemDatabase:
    def get_system_info(self, *_args, **_kwargs):
        return {"name": "Lhou Mans"}

    def get_stations(self, *_args, **_kwargs):
        return [
            {
                "name": "Ryman Enterprise",
                "type": "Coriolis Starport",
                "body": "Lhou Mans A",
                "orbit": 100.0,
                "economy": "High Tech",
                "services": ["market"],
                "allegiance": "Independent",
                "government": "Corporate",
                "controllingFaction": "Test Faction",
            }
        ]

    def get_bodies(self, *_args, **_kwargs):
        return [{"name": "Lhou Mans A", "subType": "G (White-Yellow) Star"}]


def make_prompt_generator() -> PromptGenerator:
    return PromptGenerator(
        commander_name="Dark",
        character_prompt="Cassia test prompt",
        important_game_events=[],
        system_db=FakeSystemDatabase(),
    )


def make_projected_states() -> dict:
    return {
        "CurrentStatus": {
            "GuiFocus": "NoFocus",
            "Fuel": 72.5,
            "flags": {
                "Docked": True,
                "Supercruise": False,
                "ShieldsUp": True,
                "InMainShip": True,
                "InFighter": False,
                "InSRV": False,
            },
            "flags2": {"OnFoot": False},
        },
        "InCombat": {"InCombat": False},
        "Wing": {"Members": []},
        "ShipInfo": {
            "Name": "Test Ship",
            "Type": "mediumtransport01",
            "ShipIdent": "DA-01M",
            "Cargo": 0,
            "CargoCapacity": 64,
            "LandingPadSize": "M",
            "Fighters": [],
        },
        "Cargo": {"Inventory": []},
        "Location": {
            "StarSystem": "Lhou Mans",
            "Station": "Ryman Enterprise",
            "Docked": True,
            "Factions": [
                {
                    "Name": "Citizen Party of Chireni",
                    "Government": "Communism",
                    "Influence": 62.6,
                    "FactionState": "Expansion",
                    "Happiness_Localised": "Happy",
                    "MyReputation": 2.0,
                }
            ],
            "Powers": ["Yuri Grom"],
        },
        "CommunityGoal": {
            "CurrentGoals": [
                {
                    "Title": "Lhou Mans System Defence Initiative",
                    "MarketName": "Ryman Enterprise",
                    "SystemName": "Lhou Mans",
                }
            ]
        },
        "NavInfo": {"NavRoute": [{"StarSystem": "Sol"}]},
        "Target": {},
        "StoredModules": {"ItemsInTransit": [], "Items": []},
        "StoredShips": {"ShipsInTransit": [], "ShipsRemote": []},
        "FleetCarriers": {"Carriers": {"ABC-123": {"Name": "Test Carrier", "CarrierType": "FleetCarrier", "StarSystem": "Lhou Mans"}}},
        "Missions": {"Active": []},
        "ColonisationConstruction": {"StarSystem": "Unknown"},
        "Friends": {"Online": []},
        "EngineerProgress": {
            "Engineers": [
                {"Engineer": "Felicity Farseer", "Progress": "Unlocked"},
            ]
        },
    }


def test_core_status_keeps_live_ship_and_location_context():
    status = make_prompt_generator().generate_status_message(make_projected_states(), detail="core")

    assert "# Main Ship" in status
    assert "mediumtransport01" in status
    assert "# Location" in status
    assert "Lhou Mans" in status
    assert "Ryman Enterprise" in status
    assert "Docked: true" in status


def test_core_status_omits_low_value_catalog_sections():
    status = make_prompt_generator().generate_status_message(make_projected_states(), detail="core")

    assert "Stations in local system" not in status
    assert "Bodies in local system" not in status
    assert "Factions in local system" not in status
    assert "Available Engineers" not in status
    assert "Friends Status" not in status
    assert "Community Goals" not in status
    assert "Fleet Carriers" not in status
    assert "Active missions" not in status


def test_full_status_preserves_catalog_sections_for_existing_callers():
    status = make_prompt_generator().generate_status_message(make_projected_states())

    assert "Stations in local system" in status
    assert "Bodies in local system" in status
    assert "Factions in local system" in status
    assert "Available Engineers" in status
    assert "Friends Status" in status
    assert "Community Goals" in status
    assert "Fleet Carriers" in status


def test_status_detail_uses_full_for_explicit_catalog_question():
    generator = make_prompt_generator()
    events = [ConversationEvent(kind="user", content="What stations are in this system?")]

    assert generator._choose_status_detail(events, []) == "full"


def test_status_detail_uses_core_for_routine_conversation():
    generator = make_prompt_generator()
    events = [ConversationEvent(kind="user", content="Welcome back.")]

    assert generator._choose_status_detail(events, []) == "core"


def test_status_detail_uses_full_for_catalog_event():
    generator = make_prompt_generator()
    event = GameEvent(
        content={"event": "NavRoute", "timestamp": "2026-05-07T12:00:00Z"},
        historic=False,
    )

    assert generator._choose_status_detail([event], [event]) == "full"
