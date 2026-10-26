from app.providers.base import Completion, Message


def count_tokens(text: str) -> int:
    """Un token simule par mot. Ce n'est pas le decoupage d'un vrai modele."""
    return len(text.split())


class MockProvider:
    name = "mock"
    models = frozenset({"mock-small", "mock-large"})

    def complete(self, model: str, messages: list[Message]) -> Completion:
        tokens_in = sum(count_tokens(message.content) for message in messages)
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        text = f"Reponse simulee a : {last_user[:60]}"
        return Completion(text=text, tokens_in=tokens_in, tokens_out=count_tokens(text))
