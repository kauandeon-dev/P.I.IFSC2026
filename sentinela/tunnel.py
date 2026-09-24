"""Túnel SSH para bancos de dados em outro servidor.

Abre uma porta local (127.0.0.1:porta-aleatória) que encaminha, através do
servidor SSH, para o host/porta do banco *vistos a partir do servidor SSH*
(normalmente localhost:5432 ou localhost:3306). Os clientes pg_dump/mariadb-dump
então se conectam a essa porta local, como se o banco fosse local.

Segurança da chave do host (TOFU): na primeira conexão a impressão digital do
servidor SSH é gravada; nas seguintes, se mudar, a conexão é recusada.
"""

import base64
import hashlib
import io
import logging
import select
import socket
import threading
from contextlib import contextmanager

import paramiko

from . import settings

log = logging.getLogger("sentinela")


class TunnelError(Exception):
    pass


class HostKeyMismatch(TunnelError):
    pass


def fingerprint(key):
    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def load_private_key(text, passphrase=None):
    """Aceita chaves OpenSSH/PEM (ed25519, RSA, ECDSA)."""
    text = (text or "").strip() + "\n"
    errors = []
    for cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return cls.from_private_key(io.StringIO(text), password=passphrase or None)
        except paramiko.PasswordRequiredException as e:
            raise TunnelError("A chave privada está protegida: informe a senha da chave") from e
        except (paramiko.SSHException, ValueError) as e:
            errors.append(str(e))
    raise TunnelError("Chave privada inválida ou em formato não suportado")


class _PinnedHostKey(paramiko.MissingHostKeyPolicy):
    """Aceita apenas a chave gravada; sem chave gravada, aceita e registra (TOFU)."""

    def __init__(self, expected):
        self.expected = expected
        self.seen = None

    def missing_host_key(self, client, hostname, key):
        self.seen = {"type": key.get_name(), "key": key.get_base64(), "fingerprint": fingerprint(key)}
        if self.expected and (self.expected.get("key") != key.get_base64()
                              or self.expected.get("type") != key.get_name()):
            raise HostKeyMismatch(
                f"A chave do servidor SSH mudou (agora {self.seen['fingerprint']}, "
                f"registrada {self.expected.get('fingerprint')}). Possível ataque "
                "man-in-the-middle ou servidor reinstalado. Confira e redefina a chave na tela Conexão.")


class Tunnel:
    def __init__(self, ssh, remote_host, remote_port):
        self.ssh = ssh
        self.remote = (remote_host, int(remote_port))
        self.client = None
        self.server = None
        self.local_port = None
        self.host_key = None
        self._stop = threading.Event()
        self._threads = []

    # ------------------------------------------------------------------ abrir
    def start(self):
        s = self.ssh
        policy = _PinnedHostKey(s.get("host_key"))
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(policy)
        kwargs = dict(hostname=s["host"], port=int(s.get("port") or 22), username=s["user"],
                      timeout=settings.CONNECT_TIMEOUT, banner_timeout=settings.CONNECT_TIMEOUT,
                      auth_timeout=settings.CONNECT_TIMEOUT, allow_agent=False, look_for_keys=False)
        if s.get("auth") == "key":
            kwargs["pkey"] = load_private_key(s.get("private_key"), s.get("key_passphrase"))
        else:
            kwargs["password"] = s.get("password") or ""
        try:
            client.connect(**kwargs)
        except HostKeyMismatch:
            client.close()
            raise
        except paramiko.AuthenticationException as e:
            client.close()
            raise TunnelError("Falha na autenticação SSH (usuário, senha ou chave incorretos)") from e
        except (paramiko.SSHException, OSError) as e:
            client.close()
            raise TunnelError(f"Não foi possível conectar ao servidor SSH {s['host']}:"
                              f"{s.get('port') or 22}: {e}") from e
        self.client = client
        self.host_key = policy.seen
        transport = client.get_transport()
        transport.set_keepalive(30)

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(8)
        self.server.settimeout(0.5)
        self.local_port = self.server.getsockname()[1]
        t = threading.Thread(target=self._accept_loop, daemon=True, name="sentinela-tunnel")
        t.start()
        self._threads.append(t)
        return self

    # ----------------------------------------------------------- encaminhamento
    def _accept_loop(self):
        while not self._stop.is_set():
            try:
                sock, addr = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                chan = self.client.get_transport().open_channel(
                    "direct-tcpip", self.remote, addr, timeout=settings.CONNECT_TIMEOUT)
            except Exception as e:
                log.info("Túnel SSH: não foi possível abrir canal para %s:%s — %s", *self.remote, e)
                sock.close()
                continue
            t = threading.Thread(target=self._pipe, args=(sock, chan), daemon=True)
            t.start()
            self._threads.append(t)

    def _pipe(self, sock, chan):
        try:
            while not self._stop.is_set():
                r, _, _ = select.select([sock, chan], [], [], 0.5)
                if sock in r:
                    data = sock.recv(65536)
                    if not data:
                        break
                    chan.sendall(data)
                if chan in r:
                    data = chan.recv(65536)
                    if not data:
                        break
                    sock.sendall(data)
        except (OSError, EOFError, paramiko.SSHException):
            pass
        finally:
            chan.close()
            sock.close()

    # ------------------------------------------------------------------ fechar
    def close(self):
        self._stop.set()
        if self.server:
            try:
                self.server.close()
            except OSError:
                pass
        if self.client:
            self.client.close()


@contextmanager
def open_tunnel(ssh, remote_host, remote_port):
    t = Tunnel(ssh, remote_host, remote_port).start()
    try:
        yield t
    finally:
        t.close()
