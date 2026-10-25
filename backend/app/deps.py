"""Penjaga akses (RBAC). Semua aturan peran ditegakkan DI SINI, di server.

Pola pakai:
    router = APIRouter(dependencies=[Depends(butuh_peran("guru"))])   # semua endpoint di file terkunci
    def daftar(p: Pengguna = Depends(pengguna_aktif)): ...            # endpoint terbuka untuk dua peran
"""
import ipaddress
from dataclasses import dataclass
from typing import Callable

import psycopg
from fastapi import Depends, Request

from .config import pengaturan
from .db import koneksi
from .galat import Galat
from .security import hash_token


@dataclass
class Pengguna:
    id: str
    nama: str
    peran: str  # 'guru' | 'siswa'
    nis: str | None
    tingkat: str | None
    rombel: str | None
    wajib_ganti_sandi: bool

    @property
    def kelas(self) -> str | None:
        return f"{self.tingkat} {self.rombel}" if self.tingkat else None


def sesi_pengguna(request: Request, conn: psycopg.Connection = Depends(koneksi)) -> Pengguna:
    """Pengguna dari cookie sesi. Peran dibaca dari tabel pengguna, bukan dari apa pun kiriman browser."""
    token = request.cookies.get(pengaturan().cookie_nama)
    if not token:
        raise Galat(401, "belum_login", "Silakan masuk terlebih dahulu")
    row = conn.execute(
        """select p.id, p.nama, p.peran, p.nis, p.tingkat, p.rombel, p.wajib_ganti_sandi
           from sesi s join pengguna p on p.id = s.pengguna_id
           where s.token_hash = %s and s.kedaluwarsa > now() and p.aktif""",
        (hash_token(token),),
    ).fetchone()
    if not row:
        raise Galat(401, "belum_login", "Sesi tidak berlaku, silakan masuk lagi")
    row["id"] = str(row["id"])
    return Pengguna(**row)


def pengguna_aktif(p: Pengguna = Depends(sesi_pengguna)) -> Pengguna:
    """Seperti sesi_pengguna, tapi menolak akun yang masih wajib mengganti kata sandi awal."""
    if p.wajib_ganti_sandi:
        raise Galat(403, "wajib_ganti_sandi", "Ganti kata sandi awal terlebih dahulu")
    return p


def butuh_peran(*diizinkan: str) -> Callable[..., Pengguna]:
    def cek(p: Pengguna = Depends(pengguna_aktif)) -> Pengguna:
        if p.peran not in diizinkan:
            raise Galat(403, "tidak_berwenang", "Anda tidak berwenang mengakses ini")
        return p
    return cek


def kelas_efektif(p: Pengguna, kelas_diminta: str | None) -> str | None:
    """Siswa SELALU memakai kelas dari akunnya; parameter ?kelas= dari browser diabaikan.
    Guru boleh memilih kelas (None = semua)."""
    return p.kelas if p.peran == "siswa" else kelas_diminta


UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def cek_asal(request: Request) -> None:
    """Pelengkap SameSite untuk request yang mengubah data: wajib header kustom dan Origin yang benar."""
    if request.method not in UNSAFE:
        return
    if request.headers.get("x-requested-with") != "bemai":
        raise Galat(403, "asal_tidak_valid", "Header permintaan tidak valid")
    asal = request.headers.get("origin")
    if asal and asal.rstrip("/") not in pengaturan().asal:
        raise Galat(403, "asal_tidak_valid", "Asal permintaan tidak diizinkan")


def catat_audit(conn: psycopg.Connection, aksi: str, request: Request,
                pengguna_id: str | None = None, keterangan: str | None = None) -> None:
    ip = None
    if request.client:
        try:
            ip = str(ipaddress.ip_address(request.client.host))
        except ValueError:
            ip = None  # bukan IP (unix socket, dll): jangan sampai audit menjatuhkan request
    conn.execute(
        "insert into log_audit (pengguna_id, aksi, ip, keterangan) values (%s, %s, %s, %s)",
        (pengguna_id, aksi, ip, keterangan),
    )
