"""Interface web (API JSON + página única) do Sentinela."""

import os
import shutil
import time
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, send_file, session
from werkzeug.security import check_password_hash

from . import __version__, crypto, dumpers, engine, settings, storage

STATIC = Path(__file__).parent / "static"

# Proteção simples contra força bruta no login: 5 falhas por IP => 60s de bloqueio.
_fails = {}
MAX_FAILS, LOCK_SECONDS = 5, 60


def create_app():
    storage.init()
    app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
    app.secret_key = crypto.derive(engine.key(), "sentinela/flask-session")
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.environ.get("SENTINELA_HTTPS") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=64 * 1024,
    )

    def login_required(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not session.get("user"):
                return jsonify(error="Sessão expirada. Entre novamente."), 401
            return fn(*a, **kw)
        return wrapper

    def body():
        return request.get_json(silent=True) or {}

    @app.errorhandler(ValueError)
    def _value_error(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(engine.Busy)
    def _busy(e):
        return jsonify(error=str(e)), 409

    @app.after_request
    def _headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    # ------------------------------------------------------------------ páginas

    @app.get("/")
    def index():
        return send_file(STATIC / "index.html")

    # --------------------------------------------------------------- autenticação

    @app.post("/api/login")
    def login():
        ip = request.remote_addr or "?"
        n, until = _fails.get(ip, (0, 0))
        if until > time.time():
            return jsonify(error=f"Muitas tentativas. Aguarde {int(until - time.time())}s."), 429
        data = body()
        user = storage.get_user(str(data.get("username", "")).strip())
        if not user or not check_password_hash(user["password_hash"], str(data.get("password", ""))):
            n += 1
            _fails[ip] = (0, time.time() + LOCK_SECONDS) if n >= MAX_FAILS else (n, 0)
            engine.log.info("Falha de login para '%s' a partir de %s", data.get("username"), ip)
            return jsonify(error="Usuário ou senha incorretos"), 401
        _fails.pop(ip, None)
        session.clear()
        session.permanent = True
        session["user"] = user["username"]
        engine.log.info("Login de '%s' a partir de %s", user["username"], ip)
        return jsonify(user=user["username"])

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.get("/api/me")
    def me():
        return jsonify(user=session.get("user"))

    # ------------------------------------------------------------------- estado

    @app.get("/api/state")
    @login_required
    def state():
        policy = engine.get_policy()
        conn = engine.get_connection()
        visible = storage.rows(
            "SELECT * FROM backups WHERE deleted_at IS NULL ORDER BY created_at DESC")
        ok = [b for b in visible if b["status"] == "success"]
        failed = [b for b in visible if b["status"] == "error"]
        finished = [b for b in visible if b["status"] != "running"]
        interval = engine.interval_days(policy)
        expected = max(1, -(-policy["retention_days"] // interval))  # teto
        disk = None
        try:
            du = shutil.disk_usage(policy["directory"])
            disk = {"total": du.total, "free": du.free}
        except OSError:
            pass
        nxt = engine.next_run_at()
        return jsonify(
            user=session["user"],
            version=__version__,
            policy=policy,
            connection=_public_conn(conn),
            conn_status=storage.get_setting("last_conn_test"),
            active=engine.connection_ready(conn),
            running=engine.is_busy(),
            next_run_at=storage.iso(nxt) if nxt else None,
            last_backup=_pub(finished[0]) if finished else None,
            failures={"count": len(failed), "last": _pub(failed[0]) if failed else None},
            recent=[_pub(b) for b in visible[:5]],
            storage={"copies": len(ok), "expected": expected,
                     "bytes": sum(b["size"] or 0 for b in ok), "disk": disk,
                     "directory": policy["directory"]},
            key_path=str(settings.KEY_PATH),
            limits={"retention": [settings.RETENTION_MIN, settings.RETENTION_MAX],
                    "interval": [settings.INTERVAL_MIN, settings.INTERVAL_MAX]},
        )

    # ------------------------------------------------------------------ política

    @app.put("/api/policy")
    @login_required
    def put_policy():
        return jsonify(policy=engine.save_policy(body()))

    # ------------------------------------------------------------------- conexão

    @app.put("/api/connection")
    @login_required
    def put_connection():
        return jsonify(connection=_public_conn(engine.save_connection(body())))

    @app.post("/api/connection/test")
    @login_required
    def test_connection():
        try:
            version, host_key = engine.test_connection(body())
        except (RuntimeError, dumpers.ToolNotFound) as e:
            return jsonify(ok=False, error=str(e)), 200
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 200
        return jsonify(ok=True, version=engine.short_version(version), ssh_host_key=host_key)

    # ------------------------------------------------------------------- backups

    @app.get("/api/backups")
    @login_required
    def list_backups():
        f = request.args.get("filter", "all")
        sql = "SELECT * FROM backups WHERE deleted_at IS NULL"
        args = []
        if f == "auto":
            sql += " AND trigger='auto'"
        elif f == "manual":
            sql += " AND trigger IN ('manual','pre-restore')"
        elif f == "error":
            sql += " AND status='error'"
        sql += " ORDER BY created_at DESC"
        return jsonify(backups=[_pub(b) for b in storage.rows(sql, args)])

    @app.post("/api/backups")
    @login_required
    def run_backup():
        bid = engine.start_backup("manual")
        return jsonify(id=bid), 202

    @app.get("/api/backups/<bid>")
    @login_required
    def get_backup(bid):
        b = engine.get_backup(bid)
        if not b:
            return jsonify(error="Cópia não encontrada"), 404
        lines = storage.rows("SELECT ts, level, message FROM log_lines WHERE execution_id=? "
                             "ORDER BY id", (b["execution_id"],))
        related = storage.rows(
            "SELECT id, kind, started_at, status FROM executions WHERE backup_id=? AND kind!='backup' "
            "ORDER BY id DESC LIMIT 10", (bid,))
        return jsonify(backup=_pub(b), logs=lines, executions=related)

    @app.post("/api/backups/<bid>/verify")
    @login_required
    def verify(bid):
        ok, err = engine.verify_backup(bid)
        return jsonify(ok=ok, error=err)

    @app.post("/api/backups/<bid>/restore")
    @login_required
    def restore(bid):
        exec_id = engine.start_restore(bid)
        return jsonify(execution=exec_id), 202

    @app.delete("/api/backups/<bid>")
    @login_required
    def delete(bid):
        engine.delete_backup(bid)
        return jsonify(ok=True)

    @app.get("/api/backups/<bid>/download")
    @login_required
    def download(bid):
        b = engine.get_backup(bid)
        if not b or b["status"] != "success" or b["deleted_at"] or not b["path"] \
                or not os.path.exists(b["path"]):
            return jsonify(error="Arquivo indisponível"), 404
        engine.log.info("Download da cópia %s por '%s'", bid, session["user"])
        return send_file(b["path"], as_attachment=True, download_name=os.path.basename(b["path"]),
                         mimetype="application/octet-stream")

    # ---------------------------------------------------------------------- logs

    @app.get("/api/executions/<int:eid>")
    @login_required
    def get_execution(eid):
        e = storage.row("SELECT * FROM executions WHERE id=?", (eid,))
        if not e:
            return jsonify(error="Execução não encontrada"), 404
        e["lines"] = storage.rows("SELECT ts, level, message FROM log_lines WHERE execution_id=? "
                                  "ORDER BY id", (eid,))
        return jsonify(execution=e)

    @app.get("/api/logs")
    @login_required
    def logs():
        limit = min(int(request.args.get("limit", 20)), 100)
        execs = storage.rows("SELECT * FROM executions ORDER BY id DESC LIMIT ?", (limit,))
        for e in execs:
            e["lines"] = storage.rows(
                "SELECT ts, level, message FROM log_lines WHERE execution_id=? ORDER BY id",
                (e["id"],))
        return jsonify(executions=execs)

    @app.get("/api/logs/download")
    @login_required
    def download_logs():
        if not settings.MAIN_LOG.exists():
            return jsonify(error="Nenhum log gravado ainda"), 404
        return send_file(settings.MAIN_LOG, as_attachment=True, download_name="sentinela.log",
                         mimetype="text/plain")

    return app


def _public_conn(c):
    out = {k: v for k, v in c.items() if k not in ("password_sealed", "password", "ssh")}
    out["has_password"] = bool(c.get("password_sealed"))
    ssh = c.get("ssh") or {}
    out["ssh"] = {
        "enabled": bool(ssh.get("enabled")),
        "host": ssh.get("host", ""),
        "port": ssh.get("port", "22"),
        "user": ssh.get("user", ""),
        "auth": ssh.get("auth", "password"),
        "has_password": bool(ssh.get("password_sealed")),
        "has_private_key": bool(ssh.get("private_key_sealed")),
        "has_passphrase": bool(ssh.get("key_passphrase_sealed")),
        "host_key": (ssh.get("host_key") or {}).get("fingerprint"),
    }
    out["sgbd_label"] = dumpers.SGBD_LABEL.get(c.get("sgbd"), c.get("sgbd"))
    return out


def _pub(b):
    return {
        "id": b["id"],
        "created_at": b["created_at"],
        "finished_at": b["finished_at"],
        "trigger": b["trigger"],
        "sgbd": b["sgbd"],
        "sgbd_label": dumpers.SGBD_LABEL.get(b["sgbd"], b["sgbd"]),
        "dbname": b["dbname"],
        "status": b["status"],
        "size": b["size"],
        "raw_size": b["raw_size"],
        "duration": b["duration"],
        "error": b["error"],
        "path": b["path"],
        "compressed": bool(b["compressed"]),
        "encrypted": bool(b["encrypted"]),
        "sha256": b["sha256"],
        "verified_at": b["verified_at"],
        "verify_ok": None if b["verify_ok"] is None else bool(b["verify_ok"]),
    }
