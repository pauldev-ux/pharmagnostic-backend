from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("ClaveSegura123")
    assert hashed != "ClaveSegura123"
    assert verify_password("ClaveSegura123", hashed) is True
    assert verify_password("incorrecta", hashed) is False


def test_validate_password_strength():
    # Política mínima: al menos 6 caracteres.
    assert validate_password_strength("123456") is True
    assert validate_password_strength("ClaveSegura123") is True
    assert validate_password_strength("12345") is False
    assert validate_password_strength("abc") is False


def test_access_token_roundtrip():
    token = create_access_token(7, "admin")["access_token"]
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_refresh_token_type_is_enforced():
    refresh = create_refresh_token(7, "admin")
    payload = decode_refresh_token(refresh)
    assert payload["type"] == "refresh"

    # Un access token no debe pasar como refresh.
    access = create_access_token(7, "admin")["access_token"]
    try:
        decode_refresh_token(access)
        assert False, "Debió rechazar un access token como refresh"
    except Exception:
        assert True
