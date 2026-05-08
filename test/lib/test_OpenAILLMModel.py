from src.lib.Models import OpenAILLMModel


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
