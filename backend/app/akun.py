"""Pembuatan akun. Dipakai CLI (guru) dan nanti endpoint POST /siswa, /siswa/impor, reset-sandi."""
import psycopg

from .security import hash_sandi, sandi_awal


def buat_guru(conn: psycopg.Connection, email: str, nama: str, sandi: str) -> str:
    row = conn.execute(
        """insert into pengguna (peran, nama, email, kata_sandi_hash, wajib_ganti_sandi)
           values ('guru', %s, lower(%s), %s, false) returning id""",
        (nama, email, hash_sandi(sandi)),
    ).fetchone()
    return str(row["id"])


def buat_siswa(conn: psycopg.Connection, nis: str, nama: str, tingkat: str, rombel: str) -> tuple[str, str]:
    """Mengembalikan (id, kata_sandi_awal). Sandi awal hanya ditampilkan sekali; siswa wajib menggantinya."""
    sandi = sandi_awal()
    row = conn.execute(
        """insert into pengguna (peran, nama, nis, tingkat, rombel, kata_sandi_hash)
           values ('siswa', %s, %s, %s, %s, %s) returning id""",
        (nama, nis, tingkat, rombel, hash_sandi(sandi)),
    ).fetchone()
    return str(row["id"]), sandi
