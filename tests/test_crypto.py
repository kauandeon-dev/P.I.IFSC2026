import os

import pytest

from sentinela import crypto


def _encrypt(key, data, path):
    enc = crypto.StreamEncryptor(key)
    with open(path, "wb") as f:
        f.write(enc.header())
        for i in range(0, len(data), 1000):
            f.write(enc.update(data[i:i + 1000]))
        f.write(enc.finalize())


def test_roundtrip(tmp_path):
    key = os.urandom(32)
    data = os.urandom(50_000)
    p = tmp_path / "x.enc"
    _encrypt(key, data, p)
    out = bytearray()
    crypto.decrypt_stream(p, key, out.extend)
    assert bytes(out) == data


def test_tamper_detected(tmp_path):
    key = os.urandom(32)
    p = tmp_path / "x.enc"
    _encrypt(key, b"SELECT 1;" * 1000, p)
    raw = bytearray(p.read_bytes())
    raw[100] ^= 0x01
    p.write_bytes(raw)
    with pytest.raises(crypto.IntegrityError):
        crypto.decrypt_stream(p, key)


def test_wrong_key(tmp_path):
    p = tmp_path / "x.enc"
    _encrypt(os.urandom(32), b"dados", p)
    with pytest.raises(crypto.IntegrityError):
        crypto.decrypt_stream(p, os.urandom(32))


def test_truncated(tmp_path):
    key = os.urandom(32)
    p = tmp_path / "x.enc"
    _encrypt(key, b"a" * 5000, p)
    p.write_bytes(p.read_bytes()[:-40])
    with pytest.raises(crypto.IntegrityError):
        crypto.decrypt_stream(p, key)


def test_seal_unseal():
    key = os.urandom(32)
    blob = crypto.seal(key, "s3nh@ çá")
    assert "s3nh" not in blob
    assert crypto.unseal(key, blob) == "s3nh@ çá"
    assert crypto.unseal(key, "") == ""
