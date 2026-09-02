from echotrace_api.auth import TokenError, TokenService, hash_password, verify_password


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("correct-horse-battery-staple")
    second = hash_password("correct-horse-battery-staple")
    assert first != second
    assert verify_password("correct-horse-battery-staple", first)
    assert not verify_password("wrong-password", first)


def test_token_rejects_tampering():
    service = TokenService(b"test-secret")
    token = service.issue("user-1")
    assert service.verify(token)["sub"] == "user-1"
    parts = token.split(".")
    parts[1] = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    try:
        service.verify(".".join(parts))
    except TokenError:
        pass
    else:
        raise AssertionError("tampered token was accepted")
