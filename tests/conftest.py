import importlib
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isola SENTINELA_HOME e diretório de backup por teste."""
    home = tmp_path / "home"
    backups = tmp_path / "backups"
    monkeypatch.setenv("SENTINELA_HOME", str(home))
    monkeypatch.setenv("SENTINELA_BACKUP_DIR", str(backups))
    import sentinela.settings as s
    importlib.reload(s)
    import sentinela.storage as st
    importlib.reload(st)
    import sentinela.crypto as c
    importlib.reload(c)
    import sentinela.dumpers as d
    importlib.reload(d)
    import sentinela.engine as e
    importlib.reload(e)
    e._key = None
    return {"home": home, "backups": backups, "engine": e, "storage": st}


def _pg_available():
    if not shutil.which("pg_dump"):
        return False
    p = subprocess.run(["psql", "-h", "localhost", "-U", "backup_user", "-d", "loja_producao",
                        "-w", "-tAc", "select 1"], env={**os.environ, "PGPASSWORD": "senha123"},
                       capture_output=True)
    return p.returncode == 0


def _maria_available():
    if not (shutil.which("mariadb-dump") or shutil.which("mysqldump")):
        return False
    p = subprocess.run(["mariadb", "-h", "127.0.0.1", "--protocol=TCP", "-u", "backup_user",
                        "-ps3nh@\"x", "loja_producao", "-e", "select 1"], capture_output=True)
    return p.returncode == 0


PG = {"sgbd": "postgres", "host": "localhost", "port": "5432", "dbname": "loja_producao",
      "user": "backup_user", "password": "senha123"}
MARIA = {"sgbd": "mariadb", "host": "127.0.0.1", "port": "3306", "dbname": "loja_producao",
         "user": "backup_user", "password": 's3nh@"x'}

needs_pg = pytest.mark.skipif(not _pg_available(), reason="PostgreSQL de teste indisponível")
needs_maria = pytest.mark.skipif(not _maria_available(), reason="MariaDB de teste indisponível")
