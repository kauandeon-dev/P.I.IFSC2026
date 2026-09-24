"""Núcleo do Sentinela: backup, verificação de integridade, restauração e retenção.

Pipeline de backup (em fluxo, sem arquivos intermediários em texto claro):

    SGBD --dump--> gzip --> AES-256-GCM --> arquivo .part --> rename atômico

Cada execução gera um log detalhado (banco SQLite + arquivo em disco).
"""

import hashlib
import logging
import os
import subprocess
import threading
import time
import zlib
from contextlib import contextmanager
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import crypto, dumpers, settings, storage, tunnel
from .storage import iso, now

log = logging.getLogger("sentinela")

CHUNK = 1024 * 1024

DEFAULT_POLICY = {
    "schedule_mode": "daily",      # daily | custom
    "interval_days": 2,
    "retention_days": 7,
    "directory": settings.DEFAULT_BACKUP_DIR,
    "encryption": True,
    "compression": True,
}

DEFAULT_CONNECTION = {
    "sgbd": "postgres",
    "host": "localhost",
    "port": "5432",
    "dbname": "",
    "user": "",
    "password_sealed": "",
}

# Túnel SSH opcional (banco em outro servidor). Com o túnel ativo, "host" e
# "port" da conexão são o endereço do banco visto A PARTIR do servidor SSH.
DEFAULT_SSH = {
    "enabled": False,
    "host": "",
    "port": "22",
    "user": "",
    "auth": "password",            # password | key
    "password_sealed": "",
    "private_key_sealed": "",
    "key_passphrase_sealed": "",
    "host_key": None,              # {type, key, fingerprint} gravada na 1ª conexão
}
SSH_SECRETS = ("password", "private_key", "key_passphrase")

# Chaves de host vistas em testes de conexão ainda não salvos: (host, porta) -> chave
_seen_host_keys = {}

TRIGGER_LABEL = {"auto": "automático", "manual": "manual", "pre-restore": "pré-restauração"}

# Marcadores que os clientes escrevem no FINAL de um dump completo.
DUMP_END_MARKERS = (b"PostgreSQL database dump complete", b"Dump completed")

_lock = threading.Lock()
_key = None


class Busy(Exception):
    pass


class BackupError(Exception):
    pass


# ======================================================================= setup

def setup_logging():
    settings.ensure_dirs()
    if any(isinstance(h, RotatingFileHandler) for h in log.handlers):
        return
    log.setLevel(logging.INFO)
    fh = RotatingFileHandler(settings.MAIN_LOG, maxBytes=5 * 1024 * 1024,
                             backupCount=5, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%Y-%m-%d %H:%M:%S"))
    log.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("[sentinela] %(message)s"))
    log.addHandler(sh)


def key():
    global _key
    if _key is None:
        _key = crypto.load_or_create_key()
    return _key


# ===================================================================== config

def get_policy():
    p = dict(DEFAULT_POLICY)
    p.update(storage.get_setting("policy", {}) or {})
    return p


def save_policy(data):
    cur = get_policy()
    p = dict(cur)
    if data.get("schedule_mode") in ("daily", "custom"):
        p["schedule_mode"] = data["schedule_mode"]
    if "interval_days" in data:
        p["interval_days"] = _clamp(data["interval_days"], settings.INTERVAL_MIN, settings.INTERVAL_MAX)
    if "retention_days" in data:
        p["retention_days"] = _clamp(data["retention_days"], settings.RETENTION_MIN, settings.RETENTION_MAX)
    if "encryption" in data:
        p["encryption"] = bool(data["encryption"])
    if "compression" in data:
        p["compression"] = bool(data["compression"])
    if "directory" in data:
        p["directory"] = validate_directory(data["directory"])
    storage.set_setting("policy", p)
    if (p["schedule_mode"], p["interval_days"]) != (cur["schedule_mode"], cur["interval_days"]) \
            or storage.get_setting("next_run_at") is None:
        schedule_next(from_dt=now())
    log.info("Política de backup atualizada: %s", {k: v for k, v in p.items()})
    return p


def get_connection(with_password=False):
    c = dict(DEFAULT_CONNECTION)
    c.update(storage.get_setting("connection", {}) or {})
    ssh = dict(DEFAULT_SSH)
    ssh.update(c.get("ssh") or {})
    c["ssh"] = ssh
    if with_password:
        c["password"] = crypto.unseal(key(), c.get("password_sealed", ""))
        for f in SSH_SECRETS:
            ssh[f] = crypto.unseal(key(), ssh.get(f + "_sealed", ""))
    return c


def _apply_ssh_fields(ssh, data):
    """Copia os campos não secretos do túnel SSH vindos do formulário."""
    if "enabled" in data:
        ssh["enabled"] = bool(data["enabled"])
    for f in ("host", "port", "user"):
        if f in data:
            ssh[f] = str(data[f] or "").strip()
    if data.get("auth") in ("password", "key"):
        ssh["auth"] = data["auth"]
    if ssh["port"] and not str(ssh["port"]).isdigit():
        raise ValueError("Porta SSH inválida")
    ssh["port"] = ssh["port"] or "22"


def save_connection(data):
    c = get_connection()
    if data.get("sgbd") in dumpers.SGBD_LABEL:
        c["sgbd"] = data["sgbd"]
    for f in ("host", "port", "dbname", "user"):
        if f in data:
            c[f] = str(data[f]).strip()
    if c["port"] and not c["port"].isdigit():
        raise ValueError("Porta inválida")
    if data.get("password"):
        c["password_sealed"] = crypto.seal(key(), data["password"])
    if isinstance(data.get("ssh"), dict):
        d = data["ssh"]
        ssh = c["ssh"]
        before = (ssh["host"], str(ssh["port"]))
        _apply_ssh_fields(ssh, d)
        for f in SSH_SECRETS:
            if d.get(f):
                ssh[f + "_sealed"] = crypto.seal(key(), d[f])
        if d.get("clear_private_key"):
            ssh["private_key_sealed"] = ssh["key_passphrase_sealed"] = ""
        target = (ssh["host"], str(ssh["port"]))
        if target != before or d.get("reset_host_key"):
            ssh["host_key"] = None
        if ssh["host_key"] is None and target in _seen_host_keys:
            ssh["host_key"] = _seen_host_keys.pop(target)
        if ssh["enabled"]:
            if not ssh["host"] or not ssh["user"]:
                raise ValueError("Informe o servidor e o usuário SSH")
            if ssh["auth"] == "key" and not ssh["private_key_sealed"]:
                raise ValueError("Cole a chave privada SSH")
            if ssh["auth"] == "key":
                try:
                    tunnel.load_private_key(crypto.unseal(key(), ssh["private_key_sealed"]),
                                            crypto.unseal(key(), ssh["key_passphrase_sealed"]))
                except tunnel.TunnelError as e:
                    raise ValueError(str(e)) from e
    storage.set_setting("connection", c)
    if "directory" in data:
        save_policy({"directory": data["directory"]})
    log.info("Conexão atualizada: %s em %s:%s/%s", c["sgbd"], c["host"], c["port"], c["dbname"])
    return c


def connection_ready(c=None):
    c = c or get_connection()
    return bool(c.get("dbname") and c.get("user") and c.get("sgbd"))


def test_connection(data=None):
    """Testa a conexão com os dados informados (ou os salvos)."""
    c = get_connection(with_password=True)
    if data:
        for f in ("sgbd", "host", "port", "dbname", "user"):
            if data.get(f) not in (None, ""):
                c[f] = str(data[f]).strip()
        if data.get("password"):
            c["password"] = data["password"]
        if isinstance(data.get("ssh"), dict):
            d, ssh = data["ssh"], c["ssh"]
            before = (ssh["host"], str(ssh["port"]))
            _apply_ssh_fields(ssh, d)
            for f in SSH_SECRETS:
                if d.get(f):
                    ssh[f] = d[f]
            if (ssh["host"], str(ssh["port"])) != before or d.get("reset_host_key"):
                ssh["host_key"] = None
    if not c.get("dbname"):
        raise ValueError("Informe o nome do banco")
    if c["ssh"]["enabled"] and (not c["ssh"]["host"] or not c["ssh"]["user"]):
        raise ValueError("Informe o servidor e o usuário SSH")
    info = {}
    try:
        with db_access(c, info=info) as adapter:
            version = adapter.test()
    except Exception as e:
        mark_connection(False, c["sgbd"], error=str(e))
        if isinstance(e, tunnel.TunnelError):
            raise RuntimeError(str(e)) from e
        raise
    mark_connection(True, c["sgbd"], version=version)
    return version, info.get("host_key")


@contextmanager
def db_access(conn, elog=None, info=None):
    """Entrega um adaptador pronto para uso, abrindo o túnel SSH se configurado."""
    ssh = conn.get("ssh") or {}
    port = str(conn.get("port") or dumpers.DEFAULT_PORT[conn["sgbd"]])
    if not ssh.get("enabled"):
        a = dumpers.adapter_for(conn)
        a.where = f"{a.host}:{a.port}"
        yield a
        return
    target = f"{ssh['user']}@{ssh['host']}:{ssh.get('port') or 22}"
    if elog:
        elog("INFO", f"Abrindo túnel SSH para {target}")
    try:
        t = tunnel.Tunnel(ssh, conn.get("host") or "localhost", port).start()
    except tunnel.TunnelError as e:
        mark_connection(False, conn["sgbd"], error=f"SSH: {e}")
        if elog:
            raise BackupError(f"Falha no túnel SSH: {e}") from e
        raise
    try:
        seen = t.host_key
        if seen:
            _remember_host_key(ssh, seen)
            if info is not None:
                info["host_key"] = seen["fingerprint"]
        fp = (seen or ssh.get("host_key") or {}).get("fingerprint", "")
        if elog:
            elog("OK", f"Túnel SSH estabelecido · chave do host {fp}")
        local = dict(conn, host="127.0.0.1", port=str(t.local_port))
        a = dumpers.adapter_for(local)
        a.where = f"{conn.get('host') or 'localhost'}:{port} via SSH {ssh['host']}"
        yield a
    finally:
        t.close()


def _remember_host_key(ssh, seen):
    """TOFU: grava a chave do host na primeira conexão bem-sucedida."""
    target = (ssh["host"], str(ssh.get("port") or 22))
    saved = get_connection()
    sssh = saved["ssh"]
    if (sssh["host"], str(sssh["port"])) == target and not sssh.get("host_key"):
        sssh["host_key"] = seen
        storage.set_setting("connection", saved)
        log.info("Chave do servidor SSH %s:%s registrada: %s", *target, seen["fingerprint"])
    elif (sssh["host"], str(sssh["port"])) != target:
        _seen_host_keys[target] = seen


def mark_connection(ok, sgbd, version=None, error=None):
    storage.set_setting("last_conn_test", {"ok": ok, "at": iso(now()), "sgbd": sgbd,
                                           "version": short_version(version) if version else None,
                                           "error": error})


def validate_directory(path):
    path = str(path or "").strip()
    if not path or not os.path.isabs(path):
        raise ValueError("Informe um caminho absoluto para o diretório de backup")
    p = Path(path).resolve()
    app_dir = Path(__file__).resolve().parent.parent
    for forbidden in (settings.HOME, app_dir):
        if p == forbidden or forbidden in p.parents:
            raise ValueError(
                f"O diretório de backup deve ficar isolado da aplicação (fora de {forbidden})")
    try:
        p.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as e:
        raise ValueError(f"Não foi possível criar o diretório: {e.strerror}") from e
    if not os.access(p, os.W_OK):
        raise ValueError("Sem permissão de escrita no diretório informado")
    return str(p)


def _clamp(v, lo, hi):
    try:
        v = int(v)
    except (TypeError, ValueError):
        raise ValueError("Valor numérico inválido")
    return max(lo, min(hi, v))


# ================================================================== agendamento

def interval_days(policy=None):
    policy = policy or get_policy()
    return 1 if policy["schedule_mode"] == "daily" else int(policy["interval_days"])


def schedule_next(from_dt=None, days=None):
    """Próxima execução: meia-noite, ``days`` dias depois de ``from_dt``.

    Sem ``days``, agenda para a próxima meia-noite (primeira execução)."""
    from_dt = from_dt or now()
    days = 1 if days is None else days
    nxt = datetime.combine(from_dt.date() + timedelta(days=days), datetime.min.time())
    storage.set_setting("next_run_at", iso(nxt))
    return nxt


def next_run_at():
    v = storage.get_setting("next_run_at")
    return datetime.fromisoformat(v) if v else None


# ===================================================================== logger

class ExecLog:
    """Registra cada etapa de uma execução com o horário exato."""

    def __init__(self, kind, trigger, backup_id=None, sgbd=None, dbname=None):
        self.started = now()
        self.id = storage.execute(
            "INSERT INTO executions(kind, trigger, backup_id, sgbd, dbname, started_at, status) "
            "VALUES(?,?,?,?,?,?, 'running')",
            (kind, trigger, backup_id, sgbd, dbname, iso(self.started)),
        )
        stamp = self.started.strftime("%Y%m%d_%H%M%S")
        self.file = settings.EXEC_LOG_DIR / f"{stamp}_{kind}_{self.id}.log"
        self.kind = kind
        self.trigger = trigger

    def __call__(self, level, message):
        ts = now()
        storage.execute(
            "INSERT INTO log_lines(execution_id, ts, level, message) VALUES(?,?,?,?)",
            (self.id, iso(ts), level, message),
        )
        line = f"{ts:%Y-%m-%d %H:%M:%S}  {level:<4}  {message}"
        try:
            with open(self.file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
        log.info("[%s #%s] %-4s %s", self.kind, self.id, level, message)

    def set_backup(self, backup_id):
        storage.execute("UPDATE executions SET backup_id=? WHERE id=?", (backup_id, self.id))

    def finish(self, status):
        storage.execute("UPDATE executions SET status=?, finished_at=? WHERE id=?",
                        (status, iso(now()), self.id))


# ================================================================ concorrência

def _acquire():
    if not _lock.acquire(blocking=False):
        raise Busy("Já existe uma execução em andamento. Aguarde a conclusão.")


def is_busy():
    return _lock.locked()


def _spawn(fn, *args):
    def runner():
        try:
            fn(*args)
        except Exception:
            log.exception("Erro inesperado na execução em segundo plano")
        finally:
            _lock.release()
    threading.Thread(target=runner, daemon=True, name="sentinela-exec").start()


# ===================================================================== backup

def start_backup(trigger="manual", wait=False):
    """Inicia um backup. Retorna o id da cópia.

    ``wait=True`` executa no próprio thread (usado pelo agendador e pela CLI)."""
    conn = get_connection(with_password=True)
    if not connection_ready(conn):
        raise ValueError("Configure a conexão com o banco antes de fazer backup")
    _acquire()
    try:
        ctx = _begin_backup(trigger, conn)
    except Exception:
        _lock.release()
        raise
    if wait:
        try:
            _perform_backup(*ctx)
        finally:
            _lock.release()
    else:
        _spawn(_perform_backup, *ctx)
    return ctx[1]


def _new_backup_id(ts):
    base = "bk_" + ts.strftime("%Y%m%d_%H%M%S")
    bid, n = base, 1
    while storage.row("SELECT 1 FROM backups WHERE id=?", (bid,)):
        n += 1
        bid = f"{base}_{n}"
    return bid


def _begin_backup(trigger, conn):
    policy = get_policy()
    ts = now()
    bid = _new_backup_id(ts)
    elog = ExecLog("backup", trigger, bid, conn["sgbd"], conn["dbname"])
    storage.execute(
        "INSERT INTO backups(id, execution_id, trigger, sgbd, dbname, created_at, status, "
        "compressed, encrypted) VALUES(?,?,?,?,?,?, 'running', ?, ?)",
        (bid, elog.id, trigger, conn["sgbd"], conn["dbname"], iso(ts),
         int(policy["compression"]), int(policy["encryption"])),
    )
    return elog, bid, conn, policy


def _perform_backup(elog, bid, conn, policy):
    t0 = time.monotonic()
    part = None
    try:
        elog("INFO", f"Iniciando backup {TRIGGER_LABEL.get(elog.trigger, '')} · "
                     f"{dumpers.SGBD_LABEL[conn['sgbd']]}")
        directory = Path(policy["directory"])
        try:
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        except OSError as e:
            raise BackupError(f"Diretório de backup inacessível ({directory}): {e.strerror}") from e

        with db_access(conn, elog) as adapter:
            elog("INFO", f'Conectando ao banco "{adapter.dbname}" em {adapter.where}')
            try:
                version = adapter.test()
            except Exception as e:
                mark_connection(False, adapter.sgbd, error=str(e))
                raise BackupError(f"Falha na conexão com o banco: {e}") from e
            mark_connection(True, adapter.sgbd, version=version)
            elog("OK", f"Conexão estabelecida · {short_version(version)}")

            stamp = bid[3:]
            filename = f"{safe_name(adapter.dbname)}_{stamp}.sql"
            if policy["compression"]:
                filename += ".gz"
            if policy["encryption"]:
                filename += ".enc"
            final = directory / filename
            part = directory / (filename + ".part")

            steps = ["dump"] + (["gzip"] if policy["compression"] else []) \
                + (["AES-256-GCM"] if policy["encryption"] else [])
            elog("INFO", "Gerando dump em fluxo: " + " → ".join(steps))

            stats = _stream_dump(adapter, part, policy)

        os.replace(part, final)
        part = None

        elog("OK", f"Dump gerado com sucesso ({fmt_size(stats['raw'])})")
        if policy["compression"]:
            red = (1 - stats["compressed"] / stats["raw"]) * 100 if stats["raw"] else 0
            elog("OK", f"Arquivo comprimido com gzip ({fmt_size(stats['compressed'])} · −{fmt_num(red)}%)")
        else:
            elog("WARN", "Compressão desativada na política")
        if policy["encryption"]:
            elog("OK", "Arquivo criptografado com AES-256-GCM")
        else:
            elog("WARN", "Criptografia desativada — a cópia está legível por quem acessar o diretório")
        elog("OK", f"Cópia armazenada em {final}")
        elog("INFO", f"SHA-256 {stats['sha256']}")

        # Verificação de integridade logo após a gravação
        _check_plaintext(final, policy["compression"], policy["encryption"], stats["sha256"])
        elog("OK", "Integridade verificada: arquivo legível e dump completo")

        dur = time.monotonic() - t0
        storage.execute(
            "UPDATE backups SET status='success', finished_at=?, path=?, raw_size=?, size=?, "
            "sha256=?, duration=?, verified_at=?, verify_ok=1 WHERE id=?",
            (iso(now()), str(final), stats["raw"], stats["size"], stats["sha256"], dur,
             iso(now()), bid),
        )
        elog("OK", f"Backup concluído em {fmt_duration(dur)}")
        elog.finish("success")
    except Exception as e:
        msg = str(e) if isinstance(e, (BackupError, dumpers.ToolNotFound, crypto.IntegrityError)) \
            else f"{type(e).__name__}: {e}"
        if isinstance(e, tunnel.TunnelError):
            msg = f"Falha no túnel SSH: {e}"
        if part is not None:
            try:
                part.unlink()
            except OSError:
                pass
        dur = time.monotonic() - t0
        storage.execute(
            "UPDATE backups SET status='error', finished_at=?, duration=?, error=? WHERE id=?",
            (iso(now()), dur, msg, bid),
        )
        elog("ERRO", msg)
        elog("ERRO", "Backup abortado — nenhuma cópia foi criada")
        elog.finish("error")
        if not isinstance(e, (BackupError, dumpers.ToolNotFound, tunnel.TunnelError)):
            log.exception("Detalhes do erro")
        return

    try:
        apply_retention(elog)
    except Exception as e:
        elog("WARN", f"Falha ao aplicar retenção: {e}")


def _stream_dump(adapter, part, policy):
    """Executa o dump e grava comprimido/criptografado em ``part``."""
    comp = zlib.compressobj(6, zlib.DEFLATED, 31) if policy["compression"] else None
    enc = crypto.StreamEncryptor(key()) if policy["encryption"] else None
    sha = hashlib.sha256()
    stats = {"raw": 0, "compressed": 0, "size": 0}
    tail = b""

    fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    out = os.fdopen(fd, "wb")

    def write(data):
        if not data:
            return
        out.write(data)
        sha.update(data)
        stats["size"] += len(data)

    def emit(data):
        if not data:
            return
        stats["compressed"] += len(data)
        write(enc.update(data) if enc else data)

    with adapter.dump_cmd() as (cmd, env):
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        err_chunks = []
        t = threading.Thread(target=lambda: err_chunks.append(proc.stderr.read()), daemon=True)
        t.start()
        try:
            if enc:
                write(enc.header())
            while True:
                chunk = proc.stdout.read(CHUNK)
                if not chunk:
                    break
                stats["raw"] += len(chunk)
                tail = (tail + chunk)[-512:]
                emit(comp.compress(chunk) if comp else chunk)
            if comp:
                emit(comp.flush())
            if enc:
                write(enc.finalize())
            rc = proc.wait()
            t.join(5)
        except BaseException:
            proc.kill()
            proc.wait()
            out.close()
            raise
    out.flush()
    os.fsync(out.fileno())
    out.close()

    stderr = dumpers.clean_stderr(b"".join(c for c in err_chunks if c).decode("utf-8", "replace"))
    if rc != 0:
        raise BackupError(f"Falha ao gerar dump: {stderr or f'código de saída {rc}'}")
    if stats["raw"] == 0:
        raise BackupError("Falha ao gerar dump: saída vazia")
    if not any(m in tail for m in DUMP_END_MARKERS):
        raise BackupError("Dump incompleto: marcador de conclusão ausente")
    if not comp:
        stats["compressed"] = stats["raw"]
    stats["sha256"] = sha.hexdigest()
    return stats


# ================================================================ integridade

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_plaintext(path, compressed, encrypted, sink):
    """Envia para ``sink`` o SQL original, desfazendo criptografia e compressão."""
    if compressed:
        d = zlib.decompressobj(31)

        def inner(b):
            out = d.decompress(b)
            if out:
                sink(out)
    else:
        d = None
        inner = sink

    if encrypted:
        crypto.decrypt_stream(path, key(), inner)
    else:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(CHUNK), b""):
                inner(chunk)

    if d is not None:
        rest = d.flush()
        if rest:
            sink(rest)
        if not d.eof:
            raise crypto.IntegrityError("Arquivo gzip truncado")


def _check_plaintext(path, compressed, encrypted, expected_sha=None):
    """Valida hash, autenticação, gzip e marcador de fim do dump. Retorna bytes de SQL."""
    if not os.path.exists(path):
        raise crypto.IntegrityError("Arquivo da cópia não encontrado no diretório")
    if expected_sha and file_sha256(path) != expected_sha:
        raise crypto.IntegrityError("Hash SHA-256 diferente do registrado — arquivo alterado")
    state = {"n": 0, "tail": b""}

    def sink(b):
        state["n"] += len(b)
        state["tail"] = (state["tail"] + b)[-512:]
    try:
        iter_plaintext(path, compressed, encrypted, sink)
    except zlib.error as e:
        raise crypto.IntegrityError(f"Conteúdo gzip inválido: {e}") from e
    if not any(m in state["tail"] for m in DUMP_END_MARKERS):
        raise crypto.IntegrityError("Dump incompleto: marcador de conclusão ausente")
    return state["n"]


def get_backup(bid):
    return storage.row("SELECT * FROM backups WHERE id=?", (bid,))


def verify_backup(bid):
    b = get_backup(bid)
    if not b or b["status"] != "success" or b["deleted_at"]:
        raise ValueError("Cópia indisponível para verificação")
    _acquire()
    try:
        elog = ExecLog("verify", "manual", bid, b["sgbd"], b["dbname"])
        elog("INFO", f"Verificando integridade da cópia {bid}")
        try:
            n = _check_plaintext(b["path"], b["compressed"], b["encrypted"], b["sha256"])
            elog("OK", "SHA-256 confere com o registrado")
            if b["encrypted"]:
                elog("OK", "Autenticação AES-256-GCM válida")
            elog("OK", f"Dump completo e legível ({fmt_size(n)} de SQL)")
            storage.execute("UPDATE backups SET verified_at=?, verify_ok=1 WHERE id=?",
                            (iso(now()), bid))
            elog.finish("success")
            return True, None
        except Exception as e:
            storage.execute("UPDATE backups SET verified_at=?, verify_ok=0 WHERE id=?",
                            (iso(now()), bid))
            elog("ERRO", f"Cópia inválida: {e}")
            elog.finish("error")
            return False, str(e)
    finally:
        _lock.release()


# ================================================================ restauração

def start_restore(bid, wait=False):
    b = get_backup(bid)
    if not b or b["status"] != "success" or b["deleted_at"]:
        raise ValueError("Cópia indisponível para restauração")
    conn = get_connection(with_password=True)
    if not connection_ready(conn):
        raise ValueError("Configure a conexão com o banco antes de restaurar")
    if conn["sgbd"] != b["sgbd"]:
        raise ValueError("A cópia foi gerada em outro SGBD do que o configurado na conexão")
    _acquire()
    try:
        elog = ExecLog("restore", "manual", bid, conn["sgbd"], conn["dbname"])
    except Exception:
        _lock.release()
        raise
    if wait:
        try:
            _perform_restore(elog, b, conn)
        finally:
            _lock.release()
    else:
        _spawn(_perform_restore, elog, b, conn)
    return elog.id


def _perform_restore(elog, b, conn):
    t0 = time.monotonic()
    label = dumpers.SGBD_LABEL[conn["sgbd"]]
    try:
        when = datetime.fromisoformat(b["created_at"]).strftime("%d/%m/%Y %H:%M")
        where = f"{conn['host']}:{conn['port']}" + (
            f" via SSH {conn['ssh']['host']}" if conn.get("ssh", {}).get("enabled") else "")
        elog("INFO", f"Iniciando restauração da cópia {b['id']} ({when})")
        elog("INFO", f'Destino: banco "{conn["dbname"]}" em {where}')
        _check_plaintext(b["path"], b["compressed"], b["encrypted"], b["sha256"])
        elog("OK", "Integridade da cópia verificada antes da restauração")

        # Cópia de segurança do estado atual, para permitir desfazer.
        elog("INFO", "Gerando cópia de segurança do estado atual do banco")
        try:
            ctx = _begin_backup("pre-restore", conn)
            _perform_backup(*ctx)
            pre = get_backup(ctx[1])
            if pre["status"] == "success":
                elog("OK", f"Cópia pré-restauração criada: {pre['id']}")
            else:
                elog("WARN", f"Não foi possível criar a cópia pré-restauração: {pre['error']}")
        except Exception as e:
            elog("WARN", f"Não foi possível criar a cópia pré-restauração: {e}")

        with db_access(conn, elog) as adapter, adapter.restore_cmd() as (cmd, env):
            elog("INFO", f"Aplicando o dump no {label}")
            proc = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            err_chunks = []
            t = threading.Thread(target=lambda: err_chunks.append(proc.stderr.read()), daemon=True)
            t.start()
            broken = False

            def sink(data):
                nonlocal broken
                if broken:
                    return
                try:
                    proc.stdin.write(data)
                except BrokenPipeError:
                    broken = True
            try:
                iter_plaintext(b["path"], b["compressed"], b["encrypted"], sink)
            finally:
                try:
                    proc.stdin.close()
                except BrokenPipeError:
                    pass
            rc = proc.wait()
            t.join(5)
        stderr = dumpers.clean_stderr(b"".join(c for c in err_chunks if c).decode("utf-8", "replace"))
        if rc != 0 or broken:
            raise BackupError(f"Falha ao aplicar o dump: {stderr or f'código de saída {rc}'}")
        elog("OK", f"Restauração concluída em {fmt_duration(time.monotonic() - t0)}")
        elog.finish("success")
    except Exception as e:
        elog("ERRO", str(e))
        elog("ERRO", "Restauração abortada")
        elog.finish("error")
        if not isinstance(e, (BackupError, crypto.IntegrityError, dumpers.ToolNotFound)):
            log.exception("Detalhes do erro")


# =================================================================== retenção

def apply_retention(elog=None):
    """Exclui cópias mais antigas que o período de retenção.

    A cópia válida mais recente nunca é excluída, mesmo que expirada, para que
    o sistema nunca fique sem nenhum backup restaurável."""
    days = get_policy()["retention_days"]
    cutoff = now() - timedelta(days=days)
    newest = storage.row(
        "SELECT id FROM backups WHERE status='success' AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1")
    old = storage.rows(
        "SELECT * FROM backups WHERE deleted_at IS NULL AND status!='running' AND created_at < ? "
        "ORDER BY created_at", (iso(cutoff),))
    removed = 0
    for b in old:
        if newest and b["id"] == newest["id"]:
            if elog:
                elog("WARN", f"Retenção: {b['id']} mantida por ser a cópia válida mais recente")
            continue
        _remove_file(b)
        storage.execute("UPDATE backups SET deleted_at=? WHERE id=?", (iso(now()), b["id"]))
        removed += 1
        msg = f"Retenção: cópia {b['id']} excluída (mais antiga que {days} dias)"
        if elog:
            elog("INFO", msg)
        else:
            log.info(msg)
    return removed


def delete_backup(bid):
    b = get_backup(bid)
    if not b or b["deleted_at"]:
        raise ValueError("Cópia não encontrada")
    if b["status"] == "running":
        raise ValueError("Não é possível excluir uma cópia em execução")
    _remove_file(b)
    storage.execute("UPDATE backups SET deleted_at=? WHERE id=?", (iso(now()), bid))
    log.info("Cópia %s excluída manualmente", bid)


def _remove_file(b):
    if b.get("path"):
        try:
            os.unlink(b["path"])
        except FileNotFoundError:
            pass


def recover_interrupted():
    """Marca como falha execuções que ficaram 'running' (ex.: queda do servidor)."""
    storage.execute("UPDATE backups SET status='error', error='Execução interrompida' "
                    "WHERE status='running'")
    storage.execute("UPDATE executions SET status='error', finished_at=? WHERE status='running'",
                    (iso(now()),))
    try:
        for p in Path(get_policy()["directory"]).glob("*.part"):
            p.unlink()
    except OSError:
        pass


def prune_exec_logs():
    limit = time.time() - settings.EXEC_LOG_KEEP_DAYS * 86400
    for p in settings.EXEC_LOG_DIR.glob("*.log"):
        try:
            if p.stat().st_mtime < limit:
                p.unlink()
        except OSError:
            pass


# ================================================================= formatação

def fmt_num(v, dec=1):
    return f"{v:.{dec}f}".replace(".", ",")


def fmt_size(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{int(n)} B" if unit == "B" else f"{fmt_num(n)} {unit}"
        n /= 1024


def fmt_duration(s):
    s = float(s or 0)
    if s < 60:
        return f"{max(1, round(s))}s" if s >= 0.5 else f"{fmt_num(s)}s"
    m, s = divmod(int(round(s)), 60)
    return f"{m}min {s:02d}s"


def short_version(v):
    v = (v or "").strip()
    if v.startswith("PostgreSQL"):
        return " ".join(v.split()[:2])
    if "MariaDB" in v:
        return "MariaDB " + v.split("-")[0]
    return v[:60]


def safe_name(s):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in s) or "db"
