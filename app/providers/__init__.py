from app.providers.base import Provider
from app.providers.mock import MockProvider

PROVIDERS: tuple[Provider, ...] = (MockProvider(),)


def provider_for_model(model: str) -> Provider | None:
    return next((provider for provider in PROVIDERS if model in provider.models), None)
