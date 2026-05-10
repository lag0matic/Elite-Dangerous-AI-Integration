from __future__ import annotations

from .Event import Event, ExternalEvent, GameEvent, ProjectedEvent, QuestEvent, StatusEvent
from .EventCategories import event_category
from .Projections import ProjectedStates, get_state_dict
import yaml


ContextPackResult = tuple[str, str] | None


def _dict_or_empty(value: object) -> dict:
    return value if isinstance(value, dict) else {}


class ContextPackGenerator:
    def __init__(self, pad_map: dict[str, dict[str, object]]):
        self.pad_map = pad_map

    def announce_pad(self, pad_number):
        pad = self.pad_map.get(str(pad_number))
        if not pad:
            return f"location unknown (Pad {pad_number})"

        clock = pad["clock"]
        depth = pad["depth"]
        return f"{clock} o'clock, {depth} (Pad {pad_number}, clock orientation: mail slot entry with green on right)"

    def generate_core_status_message(self, projected_states: ProjectedStates) -> str:
        current_status = _dict_or_empty(get_state_dict(projected_states, "CurrentStatus"))
        location = _dict_or_empty(get_state_dict(projected_states, "Location"))
        ship_info = _dict_or_empty(get_state_dict(projected_states, "ShipInfo"))
        cargo = _dict_or_empty(get_state_dict(projected_states, "Cargo"))
        nav_info = _dict_or_empty(get_state_dict(projected_states, "NavInfo", {"NavRoute": []}))
        in_combat = _dict_or_empty(get_state_dict(projected_states, "InCombat"))

        flags = _dict_or_empty(current_status.get("flags"))
        flags2 = _dict_or_empty(current_status.get("flags2"))

        mode = "Unknown"
        if flags2.get("OnFoot"):
            mode = "On foot"
        elif flags.get("InSRV"):
            mode = "SRV"
        elif flags.get("InFighter"):
            mode = "Ship launched fighter"
        elif flags.get("InMainShip"):
            mode = "Main ship"

        status_flags = [
            flag
            for flag in (
                "Docked",
                "Landed",
                "Supercruise",
                "FsdCharging",
                "FsdMassLocked",
                "FsdCooldown",
                "ScoopingFuel",
                "InDanger",
                "LowFuel",
                "OverHeating",
                "BeingInterdicted",
                "LandingGearDown",
                "HardpointsDeployed",
                "CargoScoopDeployed",
                "SilentRunning",
                "NightVision",
            )
            if flags.get(flag)
        ]
        if flags2:
            status_flags += [
                flag
                for flag in (
                    "FsdHyperdriveCharging",
                    "GlideMode",
                    "LowOxygen",
                    "LowHealth",
                    "VeryHot",
                    "VeryCold",
                    "OnFootInStation",
                    "OnFootOnPlanet",
                )
                if flags2.get(flag)
            ]

        location_info: dict[str, object] = {}
        if location.get("StarSystem"):
            location_info["system"] = location.get("StarSystem")
        for source_key, target_key in (
            ("Station", "station"),
            ("Planet", "planet"),
            ("PlanetaryRing", "planetary_ring"),
            ("StellarRing", "stellar_ring"),
            ("AsteroidCluster", "asteroid_cluster"),
            ("NearestDestination", "nearest_destination"),
        ):
            value = location.get(source_key)
            if value:
                location_info[target_key] = value
        if location.get("Docked") is not None:
            location_info["docked"] = location.get("Docked")
        if location.get("Landed") is not None:
            location_info["landed"] = location.get("Landed")

        ship_status: dict[str, object] = {}
        for source_key, target_key in (
            ("Name", "name"),
            ("Type", "type"),
            ("ShipIdent", "ident"),
        ):
            value = ship_info.get(source_key)
            if value and value != "Unknown":
                ship_status[target_key] = value

        cargo_count = current_status.get("Cargo", ship_info.get("Cargo"))
        cargo_capacity = cargo.get("Capacity") or ship_info.get("CargoCapacity")
        if cargo_count is not None or cargo_capacity:
            ship_status["cargo"] = {
                "current": cargo_count,
                "capacity": cargo_capacity,
            }

        fuel = current_status.get("Fuel")
        fuel_main = None
        fuel_reservoir = None
        if isinstance(fuel, dict):
            fuel_main = fuel.get("FuelMain")
            fuel_reservoir = fuel.get("FuelReservoir")
        if fuel_main is None:
            fuel_main = ship_info.get("FuelMain")
        if fuel_reservoir is None:
            fuel_reservoir = ship_info.get("FuelReservoir")
        if fuel_main is not None or fuel_reservoir is not None:
            ship_status["fuel"] = {
                "main": fuel_main,
                "main_capacity": ship_info.get("FuelMainCapacity"),
                "reservoir": fuel_reservoir,
            }

        legal_state = current_status.get("LegalState")
        if legal_state:
            ship_status["legal_state"] = legal_state

        pips = current_status.get("Pips")
        if pips:
            ship_status["pips"] = pips

        route_status: dict[str, object] = {}
        destination = current_status.get("Destination")
        if isinstance(destination, dict):
            destination_name = destination.get("Name_Localised") or destination.get("Name")
            if destination_name:
                route_status["destination"] = destination_name
        next_jump = nav_info.get("NextJumpTarget")
        if next_jump and next_jump != "Unknown":
            route_status["next_jump"] = next_jump
        nav_route = nav_info.get("NavRoute", [])
        if isinstance(nav_route, list):
            route_status["jumps_remaining"] = len(nav_route)

        core_status = {
            "mode": mode,
            "status": status_flags or "None",
            "combat": bool(in_combat.get("InCombat")),
            "location": location_info or "Unknown",
            "ship": ship_status or "Unknown",
        }
        if route_status:
            core_status["route"] = route_status

        return "# Core status\n" + yaml.dump(core_status, sort_keys=False)

    def _event_content(self, event: Event) -> dict[str, object] | None:
        if isinstance(event, (GameEvent, ProjectedEvent, ExternalEvent, QuestEvent)):
            return event.content
        if isinstance(event, StatusEvent):
            return event.status
        return None

    def _event_name(self, event: Event) -> str | None:
        content = self._event_content(event)
        if not content:
            return None
        event_name = content.get("event")
        return event_name if isinstance(event_name, str) else None

    def _copy_fields(self, content: dict[str, object], fields: tuple[tuple[str, str], ...]) -> dict[str, object]:
        entry: dict[str, object] = {}
        for source_key, target_key in fields:
            value = content.get(source_key)
            if value is not None and target_key not in entry:
                entry[target_key] = value
        return entry

    def generate_mining_context_message(self, pending_events: list[Event], projected_states: ProjectedStates) -> str | None:
        mining_events = [event for event in pending_events if event_category(event) == "Mining"]
        if not mining_events:
            return None

        location = _dict_or_empty(get_state_dict(projected_states, "Location"))
        ship_info = _dict_or_empty(get_state_dict(projected_states, "ShipInfo"))
        cargo = _dict_or_empty(get_state_dict(projected_states, "Cargo"))
        current_status = _dict_or_empty(get_state_dict(projected_states, "CurrentStatus"))
        flags = _dict_or_empty(current_status.get("flags"))

        event_entries: list[dict[str, object]] = []
        for event in mining_events:
            content = self._event_content(event)
            if not content:
                continue

            event_name = content.get("event")
            entry: dict[str, object] = {"event": event_name}

            if event_name == "ProspectedAsteroid":
                materials = []
                raw_materials = content.get("Materials", [])
                if isinstance(raw_materials, list):
                    for material in raw_materials:
                        if not isinstance(material, dict):
                            continue
                        name = material.get("Name_Localised") or material.get("Name") or "Unknown"
                        proportion = material.get("Proportion")
                        material_entry: dict[str, object] = {"name": name}
                        if proportion is not None:
                            material_entry["percent"] = proportion
                        materials.append(material_entry)
                entry["material_content"] = content.get("Content_Localised") or content.get("Content")
                entry["minerals_remaining_percent"] = content.get("Remaining")
                entry["materials"] = materials
                if content.get("MotherlodeMaterial"):
                    entry["motherlode_material"] = content.get("MotherlodeMaterial")
            elif event_name == "MiningRefined":
                entry["refined_material"] = content.get("Type_Localised") or content.get("Type")
            elif event_name == "LaunchDrone":
                entry["drone_type"] = content.get("Type_Localised") or content.get("Type")

            event_entries.append(entry)

        mining_context: dict[str, object] = {
            "events": event_entries,
            "location": {
                "system": location.get("StarSystem"),
                "planetary_ring": location.get("PlanetaryRing"),
                "stellar_ring": location.get("StellarRing"),
                "body": location.get("Planet") or location.get("Star"),
            },
            "ship": {
                "is_mining_ship": ship_info.get("IsMiningShip"),
                "has_limpet_controller": ship_info.get("hasLimpets"),
                "cargo_scoop_deployed": flags.get("CargoScoopDeployed"),
                "hardpoints_deployed": flags.get("HardpointsDeployed"),
            },
            "cargo": {
                "current": current_status.get("Cargo", ship_info.get("Cargo")),
                "capacity": cargo.get("Capacity") or ship_info.get("CargoCapacity"),
                "inventory": self._cargo_inventory_summary(cargo) or "Unknown",
            },
        }

        return "# Mining context\n" + yaml.dump(mining_context, sort_keys=False)

    def _is_station_context_event(self, event: Event) -> bool:
        event_name = self._event_name(event)
        return (
            event_category(event) == "Stations"
            or event_name in {
                "Docked",
                "Undocked",
                "DockingRequested",
                "DockingGranted",
                "DockingDenied",
                "DockingCancelled",
                "DockingCanceled",
                "DockingTimeout",
                "DockingComputerDocking",
                "DockingComputerUndocking",
                "DockingComputerDeactivated",
                "InDockingRange",
                "LandingGearDown",
                "LandingGearUp",
            }
        )

    def generate_station_context_message(self, pending_events: list[Event], projected_states: ProjectedStates) -> str | None:
        station_events = [event for event in pending_events if self._is_station_context_event(event)]
        if not station_events:
            return None

        location = _dict_or_empty(get_state_dict(projected_states, "Location"))
        current_status = _dict_or_empty(get_state_dict(projected_states, "CurrentStatus"))
        docking_events = _dict_or_empty(get_state_dict(projected_states, "DockingEvents"))
        in_docking_range = _dict_or_empty(get_state_dict(projected_states, "InDockingRange"))
        flags = _dict_or_empty(current_status.get("flags"))

        event_entries: list[dict[str, object]] = []
        for event in station_events:
            content = self._event_content(event)
            if not content:
                continue
            entry = {"event": content.get("event")}
            entry.update(self._copy_fields(content, (
                ("StationName", "station"),
                ("StationType", "station_type"),
                ("StarSystem", "system"),
                ("MarketID", "market_id"),
                ("Reason", "reason"),
            )))

            landing_pad = content.get("LandingPad")
            if landing_pad is not None:
                entry["landing_pad"] = landing_pad
                entry["pad_orientation"] = self.announce_pad(landing_pad)

            landing_pads = content.get("LandingPads")
            if landing_pads:
                entry["available_landing_pads"] = landing_pads

            event_entries.append(entry)

        station_identity: dict[str, object] = {}
        if location.get("Station"):
            station_identity["name"] = location.get("Station")
        if location.get("StarSystem"):
            station_identity["system"] = location.get("StarSystem")
        if docking_events.get("StationType") and docking_events.get("StationType") != "Unknown":
            station_identity["type"] = docking_events.get("StationType")
        if location.get("Docked") is not None:
            station_identity["docked"] = location.get("Docked")

        docking_context = {
            "last_event": docking_events.get("LastEventType"),
            "docking_computer": docking_events.get("DockingComputerState"),
            "in_docking_range": bool(
                in_docking_range.get("ReceivedFsdMassLocked")
                and in_docking_range.get("ReceivedNoFireZoneEntered")
            ),
            "no_fire_zone_entered": in_docking_range.get("ReceivedNoFireZoneEntered"),
            "mass_locked": flags.get("FsdMassLocked"),
            "landing_gear_down": flags.get("LandingGearDown"),
        }

        return "# Station context\n" + yaml.dump({
            "events": event_entries,
            "station": station_identity or "Unknown",
            "docking": docking_context,
        }, sort_keys=False)

    def generate_ship_context_message(self, pending_events: list[Event], projected_states: ProjectedStates) -> str | None:
        ship_events = [event for event in pending_events if event_category(event) == "Ship Updates"]
        if not ship_events:
            return None

        current_status = _dict_or_empty(get_state_dict(projected_states, "CurrentStatus"))
        location = _dict_or_empty(get_state_dict(projected_states, "Location"))
        ship_info = _dict_or_empty(get_state_dict(projected_states, "ShipInfo"))
        nav_info = _dict_or_empty(get_state_dict(projected_states, "NavInfo", {"NavRoute": []}))
        flags = _dict_or_empty(current_status.get("flags"))
        flags2 = _dict_or_empty(current_status.get("flags2"))

        event_entries = []
        event_names: set[str] = set()
        for event in ship_events:
            content = self._event_content(event)
            if content:
                event_name = content.get("event")
                if isinstance(event_name, str):
                    event_names.add(event_name)
                entry = {"event": event_name}
                entry.update(self._copy_fields(content, (
                    ("StarSystem", "system"),
                    ("SystemAddress", "system_address"),
                    ("JumpDist", "jump_distance"),
                    ("FuelUsed", "fuel_used"),
                    ("FuelLevel", "fuel_level"),
                    ("Name", "name"),
                    ("Name_Localised", "name_localised"),
                    ("Body", "body"),
                    ("BodyName", "body"),
                    ("StationName", "station"),
                    ("StationType", "station_type"),
                    ("Type", "type"),
                    ("Type_Localised", "type_localised"),
                    ("Threat", "threat"),
                    ("Total", "fuel_scoop_total"),
                    ("Scooped", "fuel_scooped"),
                    ("BoostValue", "boost_value"),
                )))
                event_entries.append(entry)

        mode = self._mode_from_flags(flags, flags2)
        destination = current_status.get("Destination")
        destination_name = None
        if isinstance(destination, dict):
            destination_name = destination.get("Name_Localised") or destination.get("Name")

        nav_route = nav_info.get("NavRoute", [])
        route_summary: dict[str, object] = {
            "current_system": location.get("StarSystem"),
            "destination_from_status": destination_name,
            "next_jump_target": nav_info.get("NextJumpTarget"),
        }
        if isinstance(nav_route, list):
            route_summary["jumps_remaining"] = len(nav_route)

        verified_ship_state: dict[str, object] = {
            "mode": mode,
            "docked": flags.get("Docked"),
            "landed": flags.get("Landed"),
            "supercruise": flags.get("Supercruise"),
            "fsd_charging": flags.get("FsdCharging"),
            "fsd_hyperdrive_charging": flags2.get("FsdHyperdriveCharging") if flags2 else None,
            "fsd_mass_locked": flags.get("FsdMassLocked"),
            "fsd_cooldown": flags.get("FsdCooldown"),
            "landing_gear_down": flags.get("LandingGearDown"),
            "hardpoints_deployed": flags.get("HardpointsDeployed"),
            "cargo_scoop_deployed": flags.get("CargoScoopDeployed"),
            "night_vision": flags.get("NightVision"),
            "silent_running": flags.get("SilentRunning"),
        }

        fuel_related_events = {
            "FuelScoop",
            "FuelScoopStarted",
            "FuelScoopEnded",
            "ReservoirReplenished",
            "RefuelAll",
            "RefuelPartial",
            "StartJump",
            "FSDJump",
        }
        heat_related_events = {"HeatWarning", "HeatDamage"}
        if flags.get("ScoopingFuel") or event_names.intersection(fuel_related_events):
            verified_ship_state["scooping_fuel"] = flags.get("ScoopingFuel")
        if flags.get("OverHeating") or event_names.intersection(heat_related_events):
            verified_ship_state["overheating"] = flags.get("OverHeating")
        if flags.get("LowFuel") or event_names.intersection(fuel_related_events):
            verified_ship_state["low_fuel"] = flags.get("LowFuel")

        ship: dict[str, object] = {
            "name": ship_info.get("Name"),
            "type": ship_info.get("Type"),
            "ident": ship_info.get("ShipIdent"),
            "cargo": current_status.get("Cargo", ship_info.get("Cargo")),
            "cargo_capacity": ship_info.get("CargoCapacity"),
        }
        if flags.get("LowFuel") or event_names.intersection(fuel_related_events):
            ship["fuel_main"] = ship_info.get("FuelMain")
            ship["fuel_main_capacity"] = ship_info.get("FuelMainCapacity")

        return "# Ship context\n" + yaml.dump({
            "events": event_entries,
            "verified_ship_state": verified_ship_state,
            "ship": ship,
            "navigation_context_only": route_summary,
            "interpretation_note": (
                "Route target and destination are context only. "
                "They do not mean FSD is charging, a jump is active, or mass lock is clear."
            ),
        }, sort_keys=False)

    def _mode_from_flags(self, flags: dict, flags2: dict) -> str:
        if flags2.get("OnFoot"):
            return "On foot"
        if flags.get("InSRV"):
            return "SRV"
        if flags.get("InFighter"):
            return "Ship launched fighter"
        if flags.get("InMainShip"):
            return "Main ship"
        return "Unknown"

    def generate_combat_context_message(self, pending_events: list[Event], projected_states: ProjectedStates) -> str | None:
        combat_events = [event for event in pending_events if event_category(event) == "Combat"]
        if not combat_events:
            return None

        current_status = _dict_or_empty(get_state_dict(projected_states, "CurrentStatus"))
        ship_info = _dict_or_empty(get_state_dict(projected_states, "ShipInfo"))
        loadout = _dict_or_empty(get_state_dict(projected_states, "Loadout"))
        target = _dict_or_empty(get_state_dict(projected_states, "Target"))
        in_combat = _dict_or_empty(get_state_dict(projected_states, "InCombat"))
        flags = _dict_or_empty(current_status.get("flags"))

        event_entries: list[dict[str, object]] = []
        for event in combat_events:
            content = self._event_content(event)
            if not content:
                continue
            entry = {"event": content.get("event")}
            entry.update(self._copy_fields(content, (
                ("Target", "target"),
                ("Target_Localised", "target_localised"),
                ("PilotName", "pilot"),
                ("PilotName_Localised", "pilot_localised"),
                ("Ship", "ship"),
                ("Ship_Localised", "ship_localised"),
                ("LegalStatus", "legal_status"),
                ("Faction", "faction"),
                ("Bounty", "bounty"),
                ("TotalReward", "total_reward"),
                ("Reward", "reward"),
                ("VictimFaction", "victim_faction"),
                ("AwardingFaction", "awarding_faction"),
                ("Health", "hull_health"),
                ("ShieldsUp", "shields_up"),
                ("ShieldHealth", "target_shield_health"),
                ("HullHealth", "target_hull_health"),
                ("Subsystem", "subsystem"),
                ("Subsystem_Localised", "subsystem_localised"),
                ("SubsystemHealth", "subsystem_health"),
                ("Interdictor", "interdictor"),
                ("IsPlayer", "is_player"),
                ("IsThargoid", "is_thargoid"),
            )))
            if content.get("Rewards"):
                entry["rewards"] = content.get("Rewards")
            if "TargetLocked" in content:
                entry["target_locked"] = content.get("TargetLocked")
            event_entries.append(entry)

        return "# Combat context\n" + yaml.dump({
            "events": event_entries,
            "own_ship": {
                "name": ship_info.get("Name") or loadout.get("ShipName"),
                "type": ship_info.get("Type") or loadout.get("Ship"),
                "shields_up": flags.get("ShieldsUp"),
                "hull_health": loadout.get("HullHealth"),
                "overheating": flags.get("OverHeating"),
                "hardpoints_deployed": flags.get("HardpointsDeployed"),
                "pips": current_status.get("Pips"),
                "legal_state": current_status.get("LegalState"),
            },
            "target": {
                "pilot": target.get("PilotName"),
                "ship": target.get("Ship"),
                "scan_stage": target.get("ScanStage"),
                "legal_status": target.get("LegalStatus"),
                "faction": target.get("Faction"),
                "bounty": target.get("Bounty"),
                "shield_health": target.get("ShieldHealth"),
                "hull_health": target.get("HullHealth"),
                "subsystem": target.get("Subsystem"),
                "subsystem_health": target.get("SubsystemHealth"),
            },
            "combat_state": {
                "in_combat": bool(in_combat.get("InCombat")),
                "in_danger": flags.get("InDanger"),
                "being_interdicted": flags.get("BeingInterdicted"),
            },
        }, sort_keys=False)

    def _signal_entries(self, signals: object) -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        if not isinstance(signals, list):
            return entries
        for signal in signals:
            if not isinstance(signal, dict):
                continue
            signal_type = signal.get("Type_Localised") or signal.get("Type")
            entry: dict[str, object] = {}
            if signal_type:
                entry["type"] = signal_type
            if signal.get("Count") is not None:
                entry["count"] = signal.get("Count")
            if entry:
                entries.append(entry)
        return entries

    def generate_exploration_context_message(self, pending_events: list[Event], projected_states: ProjectedStates) -> str | None:
        exploration_events = [event for event in pending_events if event_category(event) == "Exploration"]
        if not exploration_events:
            return None

        location = _dict_or_empty(get_state_dict(projected_states, "Location"))
        nav_info = _dict_or_empty(get_state_dict(projected_states, "NavInfo", {"NavRoute": []}))
        fss_signals = _dict_or_empty(get_state_dict(projected_states, "FSSSignals"))

        event_entries = []
        for event in exploration_events:
            content = self._event_content(event)
            if not content:
                continue
            entry = {"event": content.get("event")}
            entry.update(self._copy_fields(content, (
                ("StarSystem", "system"),
                ("SystemName", "system"),
                ("SystemAddress", "system_address"),
                ("JumpDist", "jump_distance"),
                ("FuelUsed", "fuel_used"),
                ("FuelLevel", "fuel_level"),
                ("SystemAllegiance", "allegiance"),
                ("SystemEconomy_Localised", "economy"),
                ("SystemEconomy", "economy"),
                ("SystemGovernment_Localised", "government"),
                ("SystemGovernment", "government"),
                ("SystemSecurity_Localised", "security"),
                ("SystemSecurity", "security"),
                ("Population", "population"),
                ("Body", "arrival_body"),
                ("BodyName", "body"),
                ("BodyID", "body_id"),
                ("BodyType", "body_type"),
                ("PlanetClass", "planet_class"),
                ("StarType", "star_type"),
                ("TerraformState", "terraform_state"),
                ("Volcanism", "volcanism"),
                ("Atmosphere", "atmosphere"),
                ("AtmosphereType", "atmosphere_type"),
                ("DistanceFromArrivalLS", "distance_from_arrival_ls"),
                ("Landable", "landable"),
                ("WasDiscovered", "was_discovered"),
                ("WasMapped", "was_mapped"),
                ("Count", "count"),
                ("SignalName", "signal_name"),
                ("Name", "name"),
                ("Name_Localised", "name_localised"),
                ("NearestDestination", "nearest_destination"),
                ("HGECandidateMaterials", "hge_candidate_materials"),
                ("HGEMatchedStates", "hge_matched_states"),
                ("Value", "value"),
                ("TotalValue", "total_value"),
            )))

            signals = self._signal_entries(content.get("Signals"))
            if signals:
                entry["signals"] = signals

            genuses = [
                genus.get("Genus_Localised") or genus.get("Genus")
                for genus in content.get("Genuses", [])
                if isinstance(genus, dict) and (genus.get("Genus_Localised") or genus.get("Genus"))
            ] if isinstance(content.get("Genuses"), list) else []
            if genuses:
                entry["genuses"] = genuses

            event_entries.append(entry)

        signal_counts: dict[str, int] = {}
        if isinstance(fss_signals, dict):
            for key, value in fss_signals.items():
                if key != "SystemAddress" and isinstance(value, list) and value:
                    signal_counts[key] = len(value)

        nav_route = nav_info.get("NavRoute", [])
        route_summary: dict[str, object] = {"next_jump_target": nav_info.get("NextJumpTarget")}
        if isinstance(nav_route, list):
            route_summary["jumps_remaining"] = len(nav_route)

        exploration_context: dict[str, object] = {
            "events": event_entries,
            "current_system": {
                "name": location.get("StarSystem"),
                "primary_star": location.get("Star"),
                "planet": location.get("Planet"),
                "planetary_ring": location.get("PlanetaryRing"),
                "stellar_ring": location.get("StellarRing"),
            },
            "route": route_summary,
        }
        if signal_counts:
            exploration_context["known_signal_counts"] = signal_counts

        return "# Exploration context\n" + yaml.dump(exploration_context, sort_keys=False)

    def generate_social_context_message(self, pending_events: list[Event], projected_states: ProjectedStates) -> str | None:
        social_events = [event for event in pending_events if event_category(event) == "Social"]
        if not social_events:
            return None

        friends = _dict_or_empty(get_state_dict(projected_states, "Friends"))
        wing = _dict_or_empty(get_state_dict(projected_states, "Wing"))

        event_entries = []
        for event in social_events:
            content = self._event_content(event)
            if not content:
                continue
            entry = {"event": content.get("event")}
            entry.update(self._copy_fields(content, (
                ("Name", "name"),
                ("Status", "status"),
                ("From_Localised", "from"),
                ("From", "from"),
                ("To", "to"),
                ("Channel", "channel"),
                ("Message_Localised", "message"),
                ("Message", "message"),
                ("SquadronName", "squadron"),
                ("Power", "power"),
                ("Amount", "amount"),
                ("Merits", "merits"),
            )))
            event_entries.append(entry)

        return "# Social context\n" + yaml.dump({
            "events": event_entries,
            "friends": {
                "online": friends.get("Online", []),
                "pending": friends.get("Pending", []),
                "online_count": len(friends.get("Online", [])) if isinstance(friends.get("Online"), list) else 0,
            },
            "wing": {
                "members": wing.get("Members", []),
                "member_count": len(wing.get("Members", [])) if isinstance(wing.get("Members"), list) else 0,
            },
        }, sort_keys=False)

    def _cargo_inventory_summary(self, cargo: dict[str, object]) -> list[dict[str, object]]:
        inventory = []
        raw_inventory = cargo.get("Inventory", [])
        if not isinstance(raw_inventory, list):
            return inventory
        for item in raw_inventory:
            if isinstance(item, dict):
                name = item.get("Name_Localised") or item.get("Name")
                count = item.get("Count")
                if name and count is not None:
                    inventory.append({"name": name, "count": count})
        return inventory

    def _matching_active_mission(self, mission_id: object, missions: dict[str, object]) -> object:
        if mission_id is None:
            return None
        active = missions.get("Active", [])
        if not isinstance(active, list):
            return None
        for mission in active:
            if isinstance(mission, dict) and mission.get("MissionID") == mission_id:
                return mission
        return None

    def generate_trading_missions_context_message(self, pending_events: list[Event], projected_states: ProjectedStates) -> str | None:
        trade_mission_events = [
            event
            for event in pending_events
            if event_category(event) in {"Trading", "Missions & Quests"}
        ]
        if not trade_mission_events:
            return None

        current_status = _dict_or_empty(get_state_dict(projected_states, "CurrentStatus"))
        cargo = _dict_or_empty(get_state_dict(projected_states, "Cargo"))
        missions = _dict_or_empty(get_state_dict(projected_states, "Missions"))
        location = _dict_or_empty(get_state_dict(projected_states, "Location"))

        event_entries = []
        matching_missions = []
        for event in trade_mission_events:
            content = self._event_content(event)
            if not content:
                continue
            entry = {"event": content.get("event")}
            entry.update(self._copy_fields(content, (
                ("Type_Localised", "commodity"),
                ("Type", "commodity"),
                ("Count", "count"),
                ("BuyPrice", "unit_buy_price"),
                ("SellPrice", "unit_sell_price"),
                ("TotalCost", "transaction_total_cost"),
                ("TotalSale", "transaction_total_sale"),
                ("AvgPricePaid", "average_price_paid"),
                ("MarketID", "market_id"),
                ("MissionID", "mission_id"),
                ("Name", "mission_name"),
                ("LocalisedName", "mission_name_localised"),
                ("Faction", "faction"),
                ("Reward", "mission_reward"),
                ("Donation", "mission_donation"),
                ("DestinationSystem", "destination_system"),
                ("DestinationStation", "destination_station"),
                ("DestinationSettlement", "destination_settlement"),
                ("NewDestinationSystem", "new_destination_system"),
                ("NewDestinationStation", "new_destination_station"),
                ("NewDestinationSettlement", "new_destination_settlement"),
                ("Target", "target"),
                ("TargetFaction", "target_faction"),
                ("TargetType_Localised", "target_type"),
                ("TargetType", "target_type"),
                ("Influence", "influence"),
                ("Reputation", "reputation"),
                ("Expiry", "expiry"),
                ("Wing", "wing"),
                ("Stolen", "stolen"),
                ("IllegalGoods", "illegal_goods"),
                ("StolenGoods", "stolen_goods"),
                ("BlackMarket", "black_market"),
                ("Abandoned", "abandoned"),
            )))
            mission = self._matching_active_mission(content.get("MissionID"), missions)
            if mission:
                matching_missions.append(mission)
            event_entries.append(entry)

        return "# Trading and missions context\n" + yaml.dump({
            "events": event_entries,
            "current_location": {
                "system": location.get("StarSystem"),
                "station": location.get("Station"),
                "docked": location.get("Docked"),
            },
            "current_finances": {
                "current_total_balance": current_status.get("Balance"),
                "note": "Transaction totals are not total credit balance.",
            },
            "cargo": {
                "current": current_status.get("Cargo", cargo.get("TotalItems")),
                "capacity": cargo.get("Capacity"),
                "inventory": self._cargo_inventory_summary(cargo) or "Unknown",
            },
            "missions": {
                "active_count": len(missions.get("Active", [])) if isinstance(missions.get("Active"), list) else 0,
                "matching_active": matching_missions or "None",
            },
        }, sort_keys=False)

    def generate_category_context_message(self, pending_events: list[Event], projected_states: ProjectedStates) -> ContextPackResult:
        if any(event_category(event) == "Mining" for event in pending_events):
            message = self.generate_mining_context_message(pending_events, projected_states)
            return ("Mining", message) if message else None
        if any(self._is_station_context_event(event) for event in pending_events):
            message = self.generate_station_context_message(pending_events, projected_states)
            return ("Stations / Docking", message) if message else None
        if any(event_category(event) == "Ship Updates" for event in pending_events):
            message = self.generate_ship_context_message(pending_events, projected_states)
            return ("Ship Updates / FSD", message) if message else None
        if any(event_category(event) == "Combat" for event in pending_events):
            message = self.generate_combat_context_message(pending_events, projected_states)
            return ("Combat", message) if message else None
        if any(event_category(event) == "Exploration" for event in pending_events):
            message = self.generate_exploration_context_message(pending_events, projected_states)
            return ("Exploration / System", message) if message else None
        if any(event_category(event) == "Social" for event in pending_events):
            message = self.generate_social_context_message(pending_events, projected_states)
            return ("Social", message) if message else None
        if any(event_category(event) in {"Trading", "Missions & Quests"} for event in pending_events):
            message = self.generate_trading_missions_context_message(pending_events, projected_states)
            return ("Trading / Missions", message) if message else None
        return None
