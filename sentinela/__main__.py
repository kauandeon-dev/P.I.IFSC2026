"""Linha de comando do Sentinela.

    python -m sentinela serve              inicia o painel web + agendador
    python -m sentinela passwd [usuario]   cria/altera usuário do painel
    python -m sentinela backup             executa um backup agora
    python -m sentinela decrypt ARQ -o SAIDA.sql
                                           recupera o SQL de uma cópia sem o painel
"""

import argparse
import getpass
import secrets
import sys
import zlib

from werkzeug.security import generate_password_hash

from . import __version__, crypto, engine, settings, storage


def cmd_serve(args):
    from .scheduler import Scheduler
    from .web import create_app

    engine.setup_logging()
    storage.init()
    engine.key()
    engine.recover_interrupted()
    if storage.count_users() == 0:
        pw = secrets.token_urlsafe(12)
        storage.upsert_user("admin", generate_password_hash(pw))
        print("=" * 60)
        print(" Primeiro acesso: usuário 'admin'  senha:", pw)
        print(" Altere com: python -m sentinela passwd admin")
        print("=" * 60)
    print(f" Chave mestra: {settings.KEY_PATH}")
    print("  -> guarde uma cópia FORA do servidor; sem ela as cópias")
    print("     criptografadas não podem ser recuperadas.")

    Scheduler().start()
    app = create_app()
    host, port = args.host or settings.HOST, args.port or settings.PORT
    engine.log.info("Sentinela %s ouvindo em http://%s:%s", __version__, host, port)
    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=8)
    except ImportError:
        app.run(host=host, port=port, threaded=True)


def cmd_passwd(args):
    storage.init()
    user = args.username or "admin"
    pw = getpass.getpass(f"Nova senha para '{user}': ")
    if len(pw) < 8:
        sys.exit("A senha deve ter pelo menos 8 caracteres.")
    if pw != getpass.getpass("Repita a senha: "):
        sys.exit("As senhas não conferem.")
    storage.upsert_user(user, generate_password_hash(pw))
    print(f"Senha de '{user}' definida.")


def cmd_backup(args):
    engine.setup_logging()
    storage.init()
    bid = engine.start_backup("manual", wait=True)
    b = engine.get_backup(bid)
    print(f"{bid}: {b['status']}" + (f" — {b['error']}" if b["error"] else f" — {b['path']}"))
    sys.exit(0 if b["status"] == "success" else 1)


def cmd_decrypt(args):
    key_path = args.key or settings.KEY_PATH
    try:
        key = _read_key(key_path)
    except OSError:
        sys.exit(f"Chave mestra não encontrada em {key_path}")
    if len(key) != crypto.KEY_LEN:
        sys.exit("Chave mestra inválida")
    src = args.file
    compressed = src.endswith(".gz") or src.endswith(".gz.enc")
    encrypted = src.endswith(".enc")
    out = sys.stdout.buffer if args.output == "-" else open(args.output, "wb")
    engine._key = key
    try:
        engine.iter_plaintext(src, compressed, encrypted, out.write)
    except (crypto.IntegrityError, zlib.error) as e:
        sys.exit(f"Erro: {e}")
    finally:
        if out is not sys.stdout.buffer:
            out.close()
    if args.output != "-":
        print(f"SQL recuperado em {args.output}")


def _read_key(path):
    with open(path, "rb") as f:
        return f.read()


def main():
    p = argparse.ArgumentParser(prog="sentinela", description="Backup automatizado de bancos de dados")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="inicia o painel web e o agendador")
    s.add_argument("--host")
    s.add_argument("--port", type=int)
    s.set_defaults(fn=cmd_serve)

    s = sub.add_parser("passwd", help="cria ou altera a senha de um usuário do painel")
    s.add_argument("username", nargs="?")
    s.set_defaults(fn=cmd_passwd)

    s = sub.add_parser("backup", help="executa um backup imediatamente")
    s.set_defaults(fn=cmd_backup)

    s = sub.add_parser("decrypt", help="recupera o SQL de uma cópia (.sql.gz.enc)")
    s.add_argument("file")
    s.add_argument("-o", "--output", required=True, help="arquivo de saída ou '-' para stdout")
    s.add_argument("--key", help="caminho da chave mestra (padrão: a do SENTINELA_HOME)")
    s.set_defaults(fn=cmd_decrypt)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
