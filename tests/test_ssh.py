"""Túnel SSH. Requer um sshd de teste em 127.0.0.1:2222 com o usuário
``tunel`` (senha ``SenhaSsh#1``) e as chaves em /tmp/sshkeys autorizadas."""

import os
import socket
import subprocess

import pytest

from conftest import MARIA, PG, needs_maria, needs_pg

KEY = "/tmp/sshkeys/id_ed25519"
KEY_PROT = "/tmp/sshkeys/id_prot"


def _ssh_available():
    try:
        socket.create_connection(("127.0.0.1", 2222), timeout=1).close()
        return os.path.exists(KEY)
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _ssh_available(), reason="sshd de teste indisponível")

SSH_PW = {"enabled": True, "host": "127.0.0.1", "port": "2222", "user": "tunel",
          "auth": "password", "password": "SenhaSsh#1"}


def _ssh_key(path=KEY, passphrase=None):
    d = {"enabled": True, "host": "127.0.0.1", "port": "2222", "user": "tunel",
         "auth": "key", "private_key": open(path).read()}
    if passphrase:
        d["key_passphrase"] = passphrase
    return d


def _setup(env, conn, ssh):
    e = env["engine"]
    e.save_policy({"directory": str(env["backups"])})
    # host/porta do banco vistos a partir do servidor SSH
    e.save_connection({**conn, "ssh": ssh})
    return e


def _lines(env, bid):
    b = env["engine"].get_backup(bid)
    return [r["message"] for r in env["storage"].rows(
        "SELECT message FROM log_lines WHERE execution_id=? ORDER BY id", (b["execution_id"],))]


@needs_pg
def test_backup_via_ssh_password(env):
    e = _setup(env, PG, SSH_PW)
    assert e.get_connection()["ssh"]["host_key"] is None
    bid = e.start_backup("manual", wait=True)
    b = e.get_backup(bid)
    assert b["status"] == "success", b["error"]
    msgs = _lines(env, bid)
    assert any("Túnel SSH estabelecido" in m for m in msgs)
    assert any("via SSH 127.0.0.1" in m for m in msgs)
    # chave do host registrada na primeira conexão (TOFU)
    hk = e.get_connection()["ssh"]["host_key"]
    assert hk and hk["fingerprint"].startswith("SHA256:")
    ok, err = e.verify_backup(bid)
    assert ok, err


@needs_pg
def test_ssh_secrets_are_sealed(env):
    _setup(env, PG, {**_ssh_key(), "password": "SenhaSsh#1"})
    raw = str(env["storage"].get_setting("connection"))
    assert "PRIVATE KEY" not in raw
    assert "SenhaSsh" not in raw


@needs_pg
def test_key_auth_and_passphrase(env):
    e = _setup(env, PG, _ssh_key())
    version, fp = e.test_connection()
    assert version.startswith("PostgreSQL")
    e2 = _setup(env, PG, _ssh_key(KEY_PROT, "frase123"))
    assert e2.test_connection()[0].startswith("PostgreSQL")


def test_protected_key_without_passphrase(env):
    e = env["engine"]
    with pytest.raises(Exception) as ex:
        e.save_connection({**PG, "ssh": _ssh_key(KEY_PROT)})
    assert "protegida" in str(ex.value)


@needs_pg
def test_wrong_ssh_password(env):
    e = _setup(env, PG, {**SSH_PW, "password": "errada"})
    with pytest.raises(RuntimeError) as ex:
        e.test_connection()
    assert "autenticação SSH" in str(ex.value)
    bid = e.start_backup("auto", wait=True)
    b = e.get_backup(bid)
    assert b["status"] == "error" and "túnel SSH" in b["error"]


@needs_pg
def test_host_key_mismatch_blocks(env):
    e = _setup(env, PG, SSH_PW)
    e.test_connection()
    c = env["storage"].get_setting("connection")
    c["ssh"]["host_key"]["key"] = "AAAAC3NzaC1lZDI1NTE5AAAAIOutraChaveFalsaQueNaoConfereComOServidor"
    env["storage"].set_setting("connection", c)
    bid = e.start_backup("auto", wait=True)
    b = e.get_backup(bid)
    assert b["status"] == "error"
    assert "mudou" in b["error"]
    # redefinir a chave libera de novo
    e.save_connection({"ssh": {"reset_host_key": True}})
    assert e.test_connection()[0]


@needs_pg
def test_restore_via_ssh(env):
    e = _setup(env, PG, SSH_PW)
    bid = e.start_backup("manual", wait=True)
    env_pg = {**os.environ, "PGPASSWORD": "senha123"}
    q = ["psql", "-h", "localhost", "-U", "backup_user", "-d", "loja_producao", "-w", "-tAc"]
    before = subprocess.run(q + ["SELECT count(*) FROM produtos"], env=env_pg,
                            capture_output=True, text=True).stdout.strip()
    subprocess.run(q + ["DELETE FROM produtos WHERE id > 10"], env=env_pg, check=True,
                   capture_output=True)
    e.start_restore(bid, wait=True)
    ex = env["storage"].row("SELECT * FROM executions WHERE kind='restore' ORDER BY id DESC")
    assert ex["status"] == "success"
    after = subprocess.run(q + ["SELECT count(*) FROM produtos"], env=env_pg,
                           capture_output=True, text=True).stdout.strip()
    assert after == before


@needs_maria
def test_mariadb_via_ssh(env):
    e = _setup(env, {**MARIA, "host": "127.0.0.1"}, SSH_PW)
    bid = e.start_backup("manual", wait=True)
    assert e.get_backup(bid)["status"] == "success", e.get_backup(bid)["error"]
