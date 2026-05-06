import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from lib.Models import GeminiCachedLLMModel


def make_model() -> GeminiCachedLLMModel:
    model = GeminiCachedLLMModel.__new__(GeminiCachedLLMModel)
    model.model_name = "gemini-2.5-flash"
    model.provider_name = "google-ai-studio"
    model.types = types
    model.cache_ttl = "10800s"
    model.cache_disabled_reason = None
    return model


class FakeCacheStore:
    def __init__(self):
        self.values = {}
        self.deleted = []

    def set(self, key, value):
        self.values[key] = value

    def delete(self, key):
        self.deleted.append(key)
        self.values.pop(key, None)


class FakeCaches:
    def __init__(self, expire_time=None, get_error=None):
        self.expire_time = expire_time
        self.get_error = get_error
        self.updated = []

    def get(self, *, name):
        if self.get_error:
            raise self.get_error
        return SimpleNamespace(name=name, expire_time=self.expire_time)

    def update(self, *, name, config):
        self.updated.append((name, config))
        return SimpleNamespace(
            name=name,
            expire_time=datetime.now(timezone.utc) + timedelta(seconds=10800),
        )


class FakeClient:
    def __init__(self, caches):
        self.caches = caches


def test_split_static_system_removes_leading_system_message():
    model = make_model()
    messages = [
        {"role": "system", "content": "static rules"},
        {"role": "user", "content": "dynamic status"},
    ]

    system_instruction, dynamic_messages = model._split_static_system(messages)

    assert system_instruction == "static rules"
    assert dynamic_messages == [{"role": "user", "content": "dynamic status"}]


def test_convert_schema_for_gemini_removes_unsupported_defaults_and_examples():
    model = make_model()
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "mode": {
                "type": "string",
                "default": "next",
                "example": "next",
                "enum": ["next", "previous"],
            }
        },
    }

    converted = model._convert_schema_for_gemini(schema)

    assert converted == {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["next", "previous"],
            }
        },
    }


def test_convert_tools_for_gemini_builds_function_declarations():
    model = make_model()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "requestDocking",
                "description": "Request docking.",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    gemini_tools = model._convert_tools_for_gemini(tools)

    assert len(gemini_tools) == 1
    tool_json = gemini_tools[0].to_json_dict()
    assert tool_json["function_declarations"][0]["name"] == "requestDocking"
    assert tool_json["function_declarations"][0]["description"] == "Request docking."


def test_build_cache_key_changes_when_tools_change():
    model = make_model()
    first_tools = model._convert_tools_for_gemini([
        {
            "type": "function",
            "function": {
                "name": "requestDocking",
                "description": "Request docking.",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ])
    second_tools = model._convert_tools_for_gemini([
        {
            "type": "function",
            "function": {
                "name": "deployHeatSink",
                "description": "Deploy heat sink",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ])

    first_hash, _ = model._build_cache_key("system", first_tools)
    second_hash, _ = model._build_cache_key("system", second_tools)

    assert first_hash != second_hash


def test_extract_tool_calls_returns_openai_compatible_tool_call():
    model = make_model()
    response = SimpleNamespace(
        function_calls=[
            SimpleNamespace(name="requestDocking", args={}),
        ]
    )

    tool_calls = model._extract_tool_calls(response)

    assert tool_calls is not None
    assert tool_calls[0].function.name == "requestDocking"
    assert json.loads(tool_calls[0].function.arguments) == {}


def test_flash_lite_models_are_allowed_to_probe_explicit_cache():
    model = make_model()
    model.model_name = "gemini-2.5-flash-lite"

    assert model._supports_explicit_cache() is True


def test_default_cache_ttl_is_three_hours():
    model = make_model()

    assert model._cache_ttl_seconds() == 10800


def test_validated_cached_content_reuses_remote_live_cache():
    model = make_model()
    model.cache_store = FakeCacheStore()
    expire_time = datetime.now(timezone.utc) + timedelta(seconds=7200)
    model.client = FakeClient(FakeCaches(expire_time=expire_time))

    cached = {"name": "cachedContents/live", "hash": "abc", "expires_at": 1}
    cache_name = model._validated_cached_content_name("cache-key", cached, "abcdef")

    assert cache_name == "cachedContents/live"
    assert model.cache_store.deleted == []
    assert model.cache_store.values["cache-key"]["expires_at"] == expire_time.timestamp()


def test_validated_cached_content_deletes_missing_remote_cache():
    model = make_model()
    model.cache_store = FakeCacheStore()
    model.cache_store.values["cache-key"] = {"name": "cachedContents/missing"}
    model.client = FakeClient(FakeCaches(get_error=RuntimeError("not found")))

    cache_name = model._validated_cached_content_name(
        "cache-key",
        {"name": "cachedContents/missing", "hash": "abc"},
        "abcdef",
    )

    assert cache_name is None
    assert model.cache_store.deleted == ["cache-key"]


def test_validated_cached_content_refreshes_near_expiry_cache():
    model = make_model()
    model.cache_store = FakeCacheStore()
    expire_time = datetime.now(timezone.utc) + timedelta(seconds=120)
    fake_caches = FakeCaches(expire_time=expire_time)
    model.client = FakeClient(fake_caches)

    cache_name = model._validated_cached_content_name(
        "cache-key",
        {"name": "cachedContents/near-expiry", "hash": "abc", "expires_at": expire_time.timestamp()},
        "abcdef",
    )

    assert cache_name == "cachedContents/near-expiry"
    assert fake_caches.updated[0][0] == "cachedContents/near-expiry"


def test_convert_auto_tool_choice_for_gemini():
    model = make_model()

    tool_config = model._convert_tool_choice_for_gemini("auto")

    config_json = tool_config.to_json_dict()
    assert config_json["function_calling_config"]["mode"] == "AUTO"


def test_convert_required_tool_choice_for_gemini():
    model = make_model()

    tool_config = model._convert_tool_choice_for_gemini("required")

    config_json = tool_config.to_json_dict()
    assert config_json["function_calling_config"]["mode"] == "ANY"


def test_convert_named_function_tool_choice_for_gemini():
    model = make_model()

    tool_config = model._convert_tool_choice_for_gemini({
        "type": "function",
        "function": {"name": "station_finder"},
    })

    config_json = tool_config.to_json_dict()
    function_config = config_json["function_calling_config"]
    assert function_config["mode"] == "ANY"
    assert function_config["allowed_function_names"] == ["station_finder"]
