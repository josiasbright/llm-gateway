from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, text

MICRO = 1_000_000


@dataclass(frozen=True)
class Price:
    """Prix en micro-dollars par million de tokens."""

    price_in_micro_per_mtok: int
    price_out_micro_per_mtok: int


def compute_cost_micro_usd(tokens_in: int, tokens_out: int, price: Price) -> int:
    """Cout arrondi au micro-dollar le plus proche (la moitie arrondie vers le haut)."""
    raw = tokens_in * price.price_in_micro_per_mtok + tokens_out * price.price_out_micro_per_mtok
    return (raw + MICRO // 2) // MICRO


def find_price(conn: Connection, provider: str, model: str, at: datetime) -> Price | None:
    """Prix valide a l'instant donne, ou rien si aucun prix n'est configure."""
    row = conn.execute(
        text(
            """
            SELECT price_in_micro_per_mtok, price_out_micro_per_mtok
            FROM model_prices
            WHERE provider = :provider AND model = :model
              AND valid_from <= :at AND (valid_to IS NULL OR valid_to > :at)
            """
        ),
        {"provider": provider, "model": model, "at": at},
    ).one_or_none()
    if row is None:
        return None
    return Price(row.price_in_micro_per_mtok, row.price_out_micro_per_mtok)
