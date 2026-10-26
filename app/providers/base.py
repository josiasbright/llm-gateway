from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True)
class Completion:
    text: str
    tokens_in: int
    tokens_out: int


class Provider(Protocol):
    name: str
    models: frozenset[str]

    def complete(self, model: str, messages: list[Message]) -> Completion: ...
