"""Caminhos e parâmetros globais, lidos de variáveis de ambiente."""

import os
from pathlib import Path

# Diretório de dados da aplicação (banco SQLite, chave mestra, logs).
# Deve ficar SEPARADO do diretório de backups.
HOME = Path(os.environ.get("SENTINELA_HOME", Path.cwd() / "data")).resolve()

DB_PATH = HOME / "sentinela.db"
KEY_PATH = HOME / "sentinela.key"
LOG_DIR = HOME / "logs"
EXEC_LOG_DIR = LOG_DIR / "execucoes"
MAIN_LOG = LOG_DIR / "sentinela.log"

DEFAULT_BACKUP_DIR = os.environ.get("SENTINELA_BACKUP_DIR", "/var/backups/sentinela")

HOST = os.environ.get("SENTINELA_BIND", "127.0.0.1")
PORT = int(os.environ.get("SENTINELA_PORT", "8080"))

# Limites da política (definidos no projeto).
RETENTION_MIN, RETENTION_MAX = 1, 10
INTERVAL_MIN, INTERVAL_MAX = 1, 30

# Tempo máximo de conexão ao SGBD (segundos).
CONNECT_TIMEOUT = int(os.environ.get("SENTINELA_CONNECT_TIMEOUT", "30"))

# Intervalo de verificação do agendador (segundos).
SCHEDULER_TICK = int(os.environ.get("SENTINELA_TICK", "30"))

# Logs de execução individuais mais antigos que isso são apagados.
EXEC_LOG_KEEP_DAYS = 90


def ensure_dirs():
    for d in (HOME, LOG_DIR, EXEC_LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(HOME, 0o700)
    except OSError:
        pass
