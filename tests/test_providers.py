from app.providers import provider_for_model
from app.providers.base import Message
from app.providers.mock import MockProvider, count_tokens


def test_count_tokens_counts_words() -> None:
    assert count_tokens("un deux trois") == 3
    assert count_tokens("") == 0


def test_mock_provider_is_deterministic() -> None:
    messages = [Message("user", "un deux trois")]
    first = MockProvider().complete("mock-small", messages)
    second = MockProvider().complete("mock-small", messages)
    assert first == second
    assert first.tokens_in == 3
    assert first.tokens_out == count_tokens(first.text)


def test_registry_finds_the_provider_of_a_model() -> None:
    provider = provider_for_model("mock-small")
    assert provider is not None
    assert provider.name == "mock"


def test_registry_returns_nothing_for_an_unknown_model() -> None:
    assert provider_for_model("inconnu") is None
