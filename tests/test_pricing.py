from app.pricing import Price, compute_cost_micro_usd

MOCK_SMALL = Price(price_in_micro_per_mtok=1_000_000, price_out_micro_per_mtok=2_000_000)


def test_cost_of_a_simple_call() -> None:
    # 12 tokens en entree a 1 $ le million, 30 en sortie a 2 $ le million : 72 micro-dollars.
    assert compute_cost_micro_usd(12, 30, MOCK_SMALL) == 72


def test_zero_tokens_cost_nothing() -> None:
    assert compute_cost_micro_usd(0, 0, MOCK_SMALL) == 0


def test_half_a_micro_dollar_rounds_up() -> None:
    price = Price(price_in_micro_per_mtok=500_000, price_out_micro_per_mtok=0)
    assert compute_cost_micro_usd(1, 0, price) == 1


def test_less_than_half_a_micro_dollar_rounds_down() -> None:
    price = Price(price_in_micro_per_mtok=499_999, price_out_micro_per_mtok=0)
    assert compute_cost_micro_usd(1, 0, price) == 0


def test_large_volumes_stay_exact() -> None:
    price = Price(price_in_micro_per_mtok=3_000_000, price_out_micro_per_mtok=15_000_000)
    assert compute_cost_micro_usd(2_000_000, 1_000_000, price) == 21_000_000
