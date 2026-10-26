from app.security import bearer_token, generate_key, hash_key, visible_prefix


def test_generated_keys_are_unique_and_prefixed() -> None:
    first, second = generate_key(), generate_key()
    assert first != second
    assert first.startswith("gw_")
    assert len(first) > 40


def test_hash_is_stable_and_differs_between_keys() -> None:
    key = generate_key()
    assert hash_key(key) == hash_key(key)
    assert hash_key(key) != hash_key(generate_key())
    assert len(hash_key(key)) == 32


def test_the_key_itself_is_not_in_its_hash() -> None:
    key = generate_key()
    assert key.encode() not in hash_key(key)


def test_visible_prefix_is_short() -> None:
    assert visible_prefix("gw_abcdefghijkl") == "gw_abcde"


def test_bearer_token_parsing() -> None:
    assert bearer_token("Bearer abc") == "abc"
    assert bearer_token("bearer abc") == "abc"
    assert bearer_token("Basic abc") is None
    assert bearer_token("Bearer ") is None
    assert bearer_token(None) is None
    assert bearer_token("") is None
