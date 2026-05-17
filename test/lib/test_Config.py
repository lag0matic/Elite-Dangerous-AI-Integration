from copy import deepcopy

from src.lib.Config import merge_config_data, update_character


def test_update_character_preserves_focus_profile_reactions(monkeypatch):
    saved_configs = []
    emitted_messages = []
    monkeypatch.setattr("src.lib.Config.save_config", lambda config: saved_configs.append(deepcopy(config)))
    monkeypatch.setattr("src.lib.Config.emit_message", lambda *args, **kwargs: emitted_messages.append((args, kwargs)))

    config = {
        "active_character_index": 0,
        "characters": [
            {
                "name": "Cassia",
                "event_reactions": {"Docked": "on"},
                "focus_profile_reactions": {},
                "personality_verbosity": 1.0,
            }
        ],
    }
    character = deepcopy(config["characters"][0])
    character["focus_profile_reactions"] = {
        "combat-focus": {
            "ReceiveText": "hidden",
            "Docked": "off",
        }
    }

    updated = update_character(config, {
        "operation": "update",
        "index": 0,
        "character": character,
    })

    assert updated["characters"][0]["focus_profile_reactions"] == {
        "combat-focus": {
            "ReceiveText": "hidden",
            "Docked": "off",
        }
    }
    assert saved_configs[-1]["characters"][0]["focus_profile_reactions"] == {
        "combat-focus": {
            "ReceiveText": "hidden",
            "Docked": "off",
        }
    }
    assert emitted_messages[-1][0] == ("config",)


def test_merge_config_data_preserves_focus_profile_reaction_keys():
    defaults = {
        "characters": [
            {
                "name": "Default",
                "event_reactions": {"Docked": "on"},
                "focus_profile_reactions": {},
            }
        ],
    }
    user = {
        "characters": [
            {
                "name": "Cassia",
                "event_reactions": {"Docked": "off"},
                "focus_profile_reactions": {
                    "combat-focus": {
                        "ReceiveText": "hidden",
                        "Docked": "off",
                    },
                },
            }
        ],
    }

    merged = merge_config_data(defaults, user)

    assert merged["characters"][0]["focus_profile_reactions"] == {
        "combat-focus": {
            "ReceiveText": "hidden",
            "Docked": "off",
        },
    }
