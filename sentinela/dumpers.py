"""Adaptadores para os SGBDs suportados (PostgreSQL e MariaDB/MySQL).

Usam os clientes oficiais de linha de comando (pg_dump/psql e
mariadb-dump/mariadb), que precisam estar instalados no servidor.
"""

import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager

from . import settings

SGBD_LABEL = {"postgres": "PostgreSQL", "mariadb": "MariaDB (MySQL)"}
DEFAULT_PORT = {"postgres": "5432", "mariadb": "3306"}


class ToolNotFound(Exception):
    pass


def _which(*names, env=None):
    if env and os.environ.get(env):
        return os.environ[env]
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    raise ToolNotFound(
        f"Cliente '{names[0]}' não encontrado no servidor. Instale o pacote cliente do SGBD."
    )


class Adapter:
    sgbd = ""

    def __init__(self, conn):
        self.host = conn.get("host") or "localhost"
        self.port = str(conn.get("port") or DEFAULT_PORT[self.sgbd])
        self.dbname = conn["dbname"]
        self.user = conn.get("user") or ""
        self.password = conn.get("password") or ""

    @property
    def label(self):
        return SGBD_LABEL[self.sgbd]

    @contextmanager
    def dump_cmd(self):
        raise NotImplementedError

    @contextmanager
    def restore_cmd(self):
        raise NotImplementedError

    @contextmanager
    def query_cmd(self, sql):
        raise NotImplementedError

    def test(self):
        """Executa uma consulta simples e devolve a versão do servidor."""
        with self.query_cmd("SELECT version()") as (cmd, env):
            p = subprocess.run(
                cmd, env=env, capture_output=True, text=True,
                timeout=settings.CONNECT_TIMEOUT + 5,
            )
        if p.returncode != 0:
            raise RuntimeError(clean_stderr(p.stderr) or f"código de saída {p.returncode}")
        return p.stdout.strip().splitlines()[0] if p.stdout.strip() else ""


class PostgresAdapter(Adapter):
    sgbd = "postgres"

    def _env(self):
        env = os.environ.copy()
        env["PGPASSWORD"] = self.password
        env["PGCONNECT_TIMEOUT"] = str(settings.CONNECT_TIMEOUT)
        env.setdefault("PGAPPNAME", "sentinela")
        return env

    def _conn_args(self):
        return ["-h", self.host, "-p", self.port, "-U", self.user, "-w"]

    @contextmanager
    def dump_cmd(self):
        # Formato texto (SQL puro) com DROP ... IF EXISTS, para que a
        # restauração substitua os objetos existentes.
        cmd = [_which("pg_dump", env="SENTINELA_PG_DUMP"), *self._conn_args(),
               "-d", self.dbname, "--format=plain", "--clean", "--if-exists",
               "--no-owner", "--encoding=UTF8"]
        yield cmd, self._env()

    @contextmanager
    def restore_cmd(self):
        cmd = [_which("psql", env="SENTINELA_PSQL"), *self._conn_args(),
               "-d", self.dbname, "-q", "-X", "-v", "ON_ERROR_STOP=1", "--single-transaction"]
        yield cmd, self._env()

    @contextmanager
    def query_cmd(self, sql):
        cmd = [_which("psql", env="SENTINELA_PSQL"), *self._conn_args(),
               "-d", self.dbname, "-X", "-tA", "-c", sql]
        yield cmd, self._env()


class MariaDBAdapter(Adapter):
    sgbd = "mariadb"

    @contextmanager
    def _defaults_file(self):
        # A senha vai num arquivo temporário (0600) para não aparecer na
        # lista de processos nem em variáveis de ambiente.
        fd, path = tempfile.mkstemp(prefix="sentinela-", suffix=".cnf")
        try:
            with os.fdopen(fd, "w") as f:
                pw = self.password.replace("\\", "\\\\").replace('"', '\\"')
                f.write(f'[client]\nuser="{self.user}"\npassword="{pw}"\n'
                        f'host="{self.host}"\nport={self.port}\n')
            yield path
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    @contextmanager
    def dump_cmd(self):
        with self._defaults_file() as cnf:
            cmd = [_which("mariadb-dump", "mysqldump", env="SENTINELA_MYSQLDUMP"),
                   f"--defaults-extra-file={cnf}", "--protocol=TCP",
                   "--single-transaction", "--quick", "--routines", "--triggers",
                   "--events", "--add-drop-table", "--hex-blob", self.dbname]
            yield cmd, os.environ.copy()

    @contextmanager
    def restore_cmd(self):
        with self._defaults_file() as cnf:
            cmd = [_which("mariadb", "mysql", env="SENTINELA_MYSQL"),
                   f"--defaults-extra-file={cnf}", "--protocol=TCP",
                   f"--connect-timeout={settings.CONNECT_TIMEOUT}", self.dbname]
            yield cmd, os.environ.copy()

    @contextmanager
    def query_cmd(self, sql):
        with self._defaults_file() as cnf:
            cmd = [_which("mariadb", "mysql", env="SENTINELA_MYSQL"),
                   f"--defaults-extra-file={cnf}", "--protocol=TCP",
                   f"--connect-timeout={settings.CONNECT_TIMEOUT}", "-N", "-B", "-D", self.dbname, "-e", sql]
            yield cmd, os.environ.copy()


def adapter_for(conn):
    sgbd = conn.get("sgbd")
    if sgbd == "postgres":
        return PostgresAdapter(conn)
    if sgbd == "mariadb":
        return MariaDBAdapter(conn)
    raise ValueError(f"SGBD não suportado: {sgbd}")


def clean_stderr(text, limit=400):
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    # Avisos inofensivos dos clientes
    lines = [ln for ln in lines if "Using a password on the command line" not in ln]
    msg = " | ".join(lines[-3:])
    return msg[:limit]
