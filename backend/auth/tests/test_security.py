import time

import jwt
import pytest

from auth import security


def test_hash_password_verifies_correct_password():
    hashed = security.hash_password("s3cret123")
    assert security.verify_password("s3cret123", hashed)


def test_hash_password_rejects_wrong_password():
    hashed = security.hash_password("s3cret123")
    assert not security.verify_password("wrong-password", hashed)


def test_hash_password_produces_different_hash_each_time():
    h1 = security.hash_password("s3cret123")
    h2 = security.hash_password("s3cret123")
    assert h1 != h2


def test_create_and_decode_access_token_roundtrip():
    token = security.create_access_token(42)
    assert security.decode_access_token(token) == 42


def test_decode_access_token_rejects_tampered_token():
    token = security.create_access_token(1)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(tampered)


def test_decode_access_token_rejects_expired_token():
    expired_payload = {"sub": "1", "exp": int(time.time()) - 60}
    expired_token = jwt.encode(expired_payload, security.JWT_SECRET, algorithm=security.JWT_ALGORITHM)
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(expired_token)


def test_decode_access_token_rejects_wrong_secret():
    token = jwt.encode({"sub": "1", "exp": int(time.time()) + 60}, "wrong-secret", algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(token)
