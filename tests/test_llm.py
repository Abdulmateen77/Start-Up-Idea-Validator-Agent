"""
Tests for the provider-neutral LLM layer (graph/llm.py + graph/providers/).

Fully offline: the Anthropic client is replaced by a recorder, so these assert the
exact request we would send and how every stop_reason is handled — without a key,
without network, without spend.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel, Field

from graph import llm
from graph.providers.anthropic_provider import AnthropicProvider, supports_effort


class Pong(BaseModel):
    answer: str


class Strict(BaseModel):
    # min_length is stripped from the schema sent to the API (it can't be enforced
    # there), so Pydantic is the only thing standing behind it.
    name: str = Field(min_length=3)


def _response(text: str | None = '{"answer": "pong"}', stop_reason: str = "end_turn", **extra):
    content = [SimpleNamespace(type="text", text=text)] if text is not None else []
    return SimpleNamespace(
        stop_reason=stop_reason, content=content, stop_details=extra.get("stop_details")
    )


class RecordingClient:
    """Stands in for anthropic.Anthropic; records every messages.create call."""

    def __init__(self, response):
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)
        self._response = response

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def _provider(response) -> tuple[AnthropicProvider, RecordingClient]:
    client = RecordingClient(response)
    return AnthropicProvider(client=client), client


def _call(provider: AnthropicProvider, **overrides):
    args = dict(
        prompt="say pong", schema=Pong, system=None, effort="medium",
        model=None, max_tokens=16000,
    )
    args.update(overrides)
    return provider.complete_structured(**args)


@pytest.fixture(autouse=True)
def _isolate_registry(monkeypatch):
    for var in ("LLM_PROVIDER", "LLM_MODEL", "LLM_MAX_TOKENS"):
        monkeypatch.delenv(var, raising=False)
    saved = dict(llm._FACTORIES)
    llm.reset_provider_cache()
    yield
    llm._FACTORIES.clear()
    llm._FACTORIES.update(saved)
    llm.reset_provider_cache()


# --------------------------------------------------------------------------- #
# Anthropic provider: the request we send
# --------------------------------------------------------------------------- #


def test_request_shape_for_current_models():
    provider, client = _provider(_response())

    result = _call(provider, system="be brief", effort="high", max_tokens=1234)

    assert result == Pong(answer="pong")
    (req,) = client.calls
    assert req["model"] == "claude-opus-5-5"
    assert req["max_tokens"] == 1234
    assert req["system"] == "be brief"
    assert req["messages"] == [{"role": "user", "content": "say pong"}]
    assert req["output_config"]["effort"] == "high"
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert req["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_never_sends_params_that_current_models_reject():
    # Disabled thinking, forced tool choice and sampling params are all 400s on
    # current Claude models. Regressing any of these breaks every run at once.
    provider, client = _provider(_response())
    _call(provider)

    (req,) = client.calls
    for forbidden in ("thinking", "tool_choice", "tools", "temperature", "top_p", "top_k"):
        assert forbidden not in req, f"{forbidden} must not be sent"


def test_system_omitted_when_not_given():
    provider, client = _provider(_response())
    _call(provider, system=None)
    assert "system" not in client.calls[0]


def test_effort_not_sent_to_models_that_reject_it():
    provider, client = _provider(_response())
    _call(provider, model="claude-haiku-4-5", effort="high")

    assert client.calls[0]["model"] == "claude-haiku-4-5"
    assert "effort" not in client.calls[0]["output_config"]
    assert "format" in client.calls[0]["output_config"]


@pytest.mark.parametrize(
    "model, expected",
    [
        ("claude-opus-5-5", True), ("claude-opus-5", True), ("claude-opus-4-8", True),
        ("claude-sonnet-5-5", True), ("claude-sonnet-4-6", True), ("claude-fable-5-1", True),
        ("claude-haiku-4-5", False), ("claude-sonnet-4-5", False), ("some-future-model", False),
    ],
)
def test_supports_effort(model, expected):
    assert supports_effort(model) is expected


# --------------------------------------------------------------------------- #
# Anthropic provider: how every outcome is handled
# --------------------------------------------------------------------------- #


def test_thinking_blocks_are_ignored():
    response = _response()
    response.content = [
        SimpleNamespace(type="thinking", thinking="..."),
        SimpleNamespace(type="text", text='{"answer": "pong"}'),
    ]
    provider, _ = _provider(response)
    assert _call(provider) == Pong(answer="pong")


def test_refusal_raises_with_category_instead_of_a_parse_error():
    response = _response(text="", stop_reason="refusal",
                         stop_details=SimpleNamespace(category="cyber"))
    provider, _ = _provider(response)

    with pytest.raises(llm.LLMRefusalError) as exc:
        _call(provider)
    assert exc.value.category == "cyber"


def test_truncation_raises_instead_of_parsing_partial_json():
    provider, _ = _provider(_response(text='{"answer": "po', stop_reason="max_tokens"))
    with pytest.raises(llm.LLMTruncatedError, match="max_tokens"):
        _call(provider, max_tokens=50)


def test_empty_response_raises():
    provider, _ = _provider(_response(text=None))
    with pytest.raises(llm.LLMEmptyResponseError):
        _call(provider)


def test_schema_mismatch_raises_llm_error():
    provider, _ = _provider(_response(text='{"wrong": 1}'))
    with pytest.raises(llm.LLMError, match="does not match Pong"):
        _call(provider)


def test_constraints_stripped_from_the_wire_are_enforced_client_side():
    provider, client = _provider(_response(text='{"name": "ab"}'))

    with pytest.raises(llm.LLMError):
        _call(provider, schema=Strict)

    # The API can't enforce minLength, so it is not sent as a schema keyword - the
    # SDK moves it into the description so the model still sees the rule as text -
    # and Pydantic is what actually rejects the violation above.
    name_field = client.calls[0]["output_config"]["format"]["schema"]["properties"]["name"]
    assert "minLength" not in name_field
    assert "minLength: 3" in name_field["description"]


# --------------------------------------------------------------------------- #
# The registry: this is what makes the layer model-agnostic
# --------------------------------------------------------------------------- #


def test_anthropic_is_the_default_and_needs_no_credentials_to_construct(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(var, raising=False)

    provider = llm.get_provider()

    assert provider.name == "anthropic"
    assert provider.default_model == "claude-opus-5-5"


def test_unknown_provider_fails_loudly_and_lists_options(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError, match="anthropic"):
        llm.get_provider()


def test_a_new_provider_plugs_in_with_no_node_changes(monkeypatch):
    seen: dict = {}

    class FakeProvider:
        name = "fake"
        default_model = "fake-1"

        def complete_structured(self, *, prompt, schema, system, effort, model, max_tokens):
            seen.update(prompt=prompt, system=system, effort=effort,
                        model=model, max_tokens=max_tokens)
            return schema(answer="from-fake")

    llm.register_provider("fake", FakeProvider)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_MODEL", "fake-xl")

    # Exactly what a node does - it has no idea which vendor answered.
    result = llm.generate_structured("hello", Pong, effort="high", system_instruction="sys")

    assert result == Pong(answer="from-fake")
    assert seen == {"prompt": "hello", "system": "sys", "effort": "high",
                    "model": "fake-xl", "max_tokens": 16000}
    assert "fake" in llm.available_providers()


def test_max_tokens_is_configurable_by_env_and_by_argument(monkeypatch):
    seen: list[int] = []

    class Capture:
        name = "cap"
        default_model = "cap"

        def complete_structured(self, **kw):
            seen.append(kw["max_tokens"])
            return Pong(answer="x")

    llm.register_provider("cap", Capture)
    monkeypatch.setenv("LLM_PROVIDER", "cap")

    monkeypatch.setenv("LLM_MAX_TOKENS", "4000")
    llm.generate_structured("p", Pong)
    llm.generate_structured("p", Pong, max_tokens=999)

    assert seen == [4000, 999]
