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


@needs_pg
def test_live_logs_state_chart_and_health(env):
    c = _client(env)
    _login(c)
    c.put("/api/policy", json={"directory": str(env["backups"])})
    c.put("/api/connection", json=PG)
    s = c.get("/api/state").get_json()
    assert s["current"] is None and s["chart"] == []
    assert any(h["title"] == "Nenhuma cópia válida ainda" for h in s["health"])

    base = c.get("/api/logs").get_json()["last_id"]
    bid = c.post("/api/backups").get_json()["id"]
    cur = c.get("/api/state").get_json()["current"]
    assert cur is None or (cur["kind"] == "backup" and cur["backup_id"] == bid)
    seen, since = [], base
    for _ in range(300):
        t = c.get(f"/api/logs/tail?since={since}").get_json()
        seen += t["lines"]
        assert all(ln["id"] > since for ln in t["lines"])
        since = t["last_id"]
        if not t["running"] and any("Backup concluído" in ln["message"] for ln in seen):
            break
        time.sleep(0.05)
    msgs = [ln["message"] for ln in seen]
    assert msgs[0].startswith("Iniciando backup manual")
    assert "Backup concluído" in msgs[-1] or any("Backup concluído" in m for m in msgs)
    ids = [ln["id"] for ln in seen]
    assert ids == sorted(ids) and len(ids) == len(set(ids))  # sem linhas repetidas

    # nada novo depois do fim
    t = c.get(f"/api/logs/tail?since={since}").get_json()
    assert t["lines"] == [] and t["running"] is False and t["current"] is None

    s = c.get("/api/state").get_json()
    assert [b["id"] for b in s["chart"]] == [bid]
    titles = {h["title"]: h["state"] for h in s["health"]}
    assert titles["Cópia recente disponível"] == "ok"
    assert titles["Integridade verificada"] == "ok"
    assert titles["Criptografia AES-256"] == "ok"


def test_progress_interval():
    from sentinela import engine
    assert engine._progress_interval(0) == 2
    assert engine._progress_interval(45) == 10
    assert engine._progress_interval(3600) == 60
