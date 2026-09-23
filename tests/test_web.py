import time

from werkzeug.security import generate_password_hash

from conftest import PG, needs_pg


def _client(env):
    import importlib
    import sentinela.web as web
    importlib.reload(web)
    env["storage"].upsert_user("admin", generate_password_hash("senha-forte-123"))
    return web.create_app().test_client()


def _login(c):
    r = c.post("/api/login", json={"username": "admin", "password": "senha-forte-123"})
    assert r.status_code == 200


def test_requires_login(env):
    c = _client(env)
    assert c.get("/api/state").status_code == 401
    assert c.post("/api/login", json={"username": "admin", "password": "x"}).status_code == 401
    _login(c)
    assert c.get("/api/state").status_code == 200


def test_bruteforce_lock(env):
    c = _client(env)
    for _ in range(5):
        c.post("/api/login", json={"username": "admin", "password": "x"})
    r = c.post("/api/login", json={"username": "admin", "password": "senha-forte-123"})
    assert r.status_code == 429


def test_password_never_returned(env):
    c = _client(env)
    _login(c)
    r = c.put("/api/connection", json={**PG, "password": "segredo!"})
    assert r.status_code == 200
    assert b"segredo" not in r.data
    s = c.get("/api/state").get_json()
    assert s["connection"]["has_password"] is True
    assert "password_sealed" not in s["connection"]


def test_invalid_directory(env):
    c = _client(env)
    _login(c)
    r = c.put("/api/policy", json={"directory": "nao/absoluto"})
    assert r.status_code == 400


@needs_pg
def test_full_flow(env):
    c = _client(env)
    _login(c)
    c.put("/api/policy", json={"directory": str(env["backups"])})
    c.put("/api/connection", json=PG)
    assert c.post("/api/connection/test", json={}).get_json()["ok"]
    r = c.post("/api/backups")
    assert r.status_code == 202
    bid = r.get_json()["id"]
    for _ in range(100):
        b = c.get(f"/api/backups/{bid}").get_json()["backup"]
        if b["status"] != "running":
            break
        time.sleep(0.1)
    assert b["status"] == "success"
    while c.get("/api/state").get_json()["running"]:
        time.sleep(0.1)
    d = c.get(f"/api/backups/{bid}/download")
    assert d.status_code == 200 and d.data[:4] == b"SNTL"
    assert c.get("/api/logs").get_json()["executions"]
    assert c.get("/api/backups?filter=manual").get_json()["backups"][0]["id"] == bid
    assert c.delete(f"/api/backups/{bid}").status_code == 200
    assert c.get("/api/backups").get_json()["backups"] == []
