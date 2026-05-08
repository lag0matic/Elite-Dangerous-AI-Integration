from src.lib.Models import OpenAILLMModel, OpenAIResponsesLLMModel


class _FakeResponses:
    def __init__(self) -> None:
        self.params = None

    def create(self, **params):
        self.params = params
        return type("Response", (), {"output_text": "ok", "usage": None, "output": []})()


class _FakeResponsesClient:
    def __init__(self) -> None:
        self.responses = _FakeResponses()


def test_together_disabled_reasoning_is_ignored() -> None:
    model = OpenAILLMModel(
        base_url="https://api.together.ai/v1",
        api_key="test-key",
        model_name="MiniMaxAI/MiniMax-M2.7",
        temperature=1.0,
        reasoning_effort="disabled",
        provider_name="custom",
    )

    params, extra_body = model._reasoning_request_overrides()

    assert params == {}
    assert extra_body == {}


def test_together_minimal_reasoning_is_ignored() -> None:
    model = OpenAILLMModel(
        base_url="https://api.together.ai/v1",
        api_key="test-key",
        model_name="MiniMaxAI/MiniMax-M2.7",
        temperature=1.0,
        reasoning_effort="minimal",
        provider_name="custom",
    )

    params, extra_body = model._reasoning_request_overrides()

    assert params == {}
    assert extra_body == {}


def test_together_low_reasoning_uses_reasoning_effort() -> None:
    model = OpenAILLMModel(
        base_url="https://api.together.ai/v1",
        api_key="test-key",
        model_name="MiniMaxAI/MiniMax-M2.7",
        temperature=1.0,
        reasoning_effort="low",
        provider_name="custom",
    )

    params, extra_body = model._reasoning_request_overrides()

    assert params == {"reasoning_effort": "low"}
    assert extra_body == {}


def test_disabled_reasoning_is_ignored_for_standard_openai_compatible_hosts() -> None:
    model = OpenAILLMModel(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model_name="custom-model",
        temperature=1.0,
        reasoning_effort="disabled",
        provider_name="custom",
    )

    params, extra_body = model._reasoning_request_overrides()

    assert params == {}
    assert extra_body == {}


def test_openai_responses_gpt5_family_omits_temperature() -> None:
    model = OpenAIResponsesLLMModel(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model_name="gpt-5.4-mini",
        temperature=0.5,
        reasoning_effort="low",
        provider_name="openai",
    )
    fake_client = _FakeResponsesClient()
    model.client = fake_client

    model.generate(messages=[{"role": "user", "content": "test"}])

    assert "temperature" not in fake_client.responses.params
    assert fake_client.responses.params["text"] == {"verbosity": "low"}


def test_openai_responses_non_gpt5_keeps_temperature() -> None:
    model = OpenAIResponsesLLMModel(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model_name="gpt-4.1-mini",
        temperature=0.5,
        reasoning_effort="default",
        provider_name="openai",
    )
    fake_client = _FakeResponsesClient()
    model.client = fake_client

    model.generate(messages=[{"role": "user", "content": "test"}])

    assert fake_client.responses.params["temperature"] == 0.5
