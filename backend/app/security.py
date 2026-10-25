import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_ph = PasswordHasher()  # argon2id, parameter bawaan library
# Hash tiruan: dipakai saat akun tidak ditemukan, supaya waktu respons tidak membedakan
# "akun tidak ada" dari "sandi salah".
_DUMMY = _ph.hash("bemai-dummy-tidak-dipakai")


def hash_sandi(sandi: str) -> str:
    return _ph.hash(sandi)


def cek_sandi(hash_tersimpan: str | None, sandi: str) -> bool:
    try:
        return _ph.verify(hash_tersimpan or _DUMMY, sandi) and hash_tersimpan is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def buat_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def sandi_awal() -> str:
    """Kata sandi awal acak, ditampilkan sekali ke guru untuk dibagikan."""
    abjad = "abcdefghjkmnpqrstuvwxyz23456789"  # tanpa karakter yang mirip (l, 1, o, 0, i)
    return "".join(secrets.choice(abjad) for _ in range(10))
