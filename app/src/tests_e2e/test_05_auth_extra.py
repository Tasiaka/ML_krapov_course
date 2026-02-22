def test_repeat_authorization_is_ok(client, user):
    """
    Повторная авторизация (re-login):
    - логинимся ещё раз теми же кредами
    - получаем 200 и access_token
    """
    r = client.post(
        "/auth/login",
        json={"email": user.email, "password": user.password},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 10



