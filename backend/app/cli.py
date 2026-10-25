"""Perintah administrasi.  Contoh:  python -m app.cli buat-guru --email bu.rina@sekolah.sch.id --nama "Bu Rina"
Tidak ada pendaftaran publik; akun guru pertama dibuat dari sini.
Lupa sandi guru juga diselesaikan dari sini: python -m app.cli reset-sandi --email ...
"""
import argparse
import getpass
import sys

import psycopg
from psycopg.rows import dict_row

from .akun import buat_guru
from .config import pengaturan
from .security import hash_sandi, sandi_awal


def _reset_sandi_guru(conn, email: str) -> int:
    row = conn.execute(
        "select id, nama from pengguna where peran = 'guru' and lower(email) = lower(%s)",
        (email.strip(),),
    ).fetchone()
    if not row:
        print(f"Guru dengan email {email} tidak ditemukan.", file=sys.stderr)
        return 1
    sandi = sandi_awal()
    conn.execute(
        """update pengguna set kata_sandi_hash = %s, wajib_ganti_sandi = true,
           gagal_login = 0, terkunci_sampai = null where id = %s""",
        (hash_sandi(sandi), row["id"]),
    )
    conn.execute("delete from sesi where pengguna_id = %s", (row["id"],))
    print(f"Sandi baru untuk {row['nama']} ({email}): {sandi}")
    print("Wajib diganti saat login berikutnya. Simpan sekarang, hanya muncul sekali.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="app.cli")
    sub = ap.add_subparsers(dest="perintah", required=True)

    g = sub.add_parser("buat-guru")
    g.add_argument("--email", required=True)
    g.add_argument("--nama", required=True)

    r = sub.add_parser("reset-sandi", help="Buat kata sandi baru untuk akun guru")
    r.add_argument("--email", required=True)

    a = ap.parse_args()

    if a.perintah == "reset-sandi":
        with psycopg.connect(pengaturan().database_url, row_factory=dict_row) as conn:
            return _reset_sandi_guru(conn, a.email)

    sandi = getpass.getpass("Kata sandi (min 10 karakter): ")
    if len(sandi) < 10 or sandi != getpass.getpass("Ulangi: "):
        print("Kata sandi kurang dari 10 karakter atau tidak sama.", file=sys.stderr)
        return 1
    with psycopg.connect(pengaturan().database_url, row_factory=dict_row) as conn:
        print("Guru dibuat, id:", buat_guru(conn, a.email, a.nama, sandi))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
