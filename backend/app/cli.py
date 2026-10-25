"""Perintah administrasi.  Contoh:  python -m app.cli buat-guru --email bu.rina@sekolah.sch.id --nama "Bu Rina"
Tidak ada pendaftaran publik; akun guru pertama dibuat dari sini."""
import argparse
import getpass
import sys

import psycopg
from psycopg.rows import dict_row

from .akun import buat_guru
from .config import pengaturan


def main() -> int:
    ap = argparse.ArgumentParser(prog="app.cli")
    sub = ap.add_subparsers(dest="perintah", required=True)
    g = sub.add_parser("buat-guru")
    g.add_argument("--email", required=True)
    g.add_argument("--nama", required=True)
    a = ap.parse_args()

    sandi = getpass.getpass("Kata sandi (min 10 karakter): ")
    if len(sandi) < 10 or sandi != getpass.getpass("Ulangi: "):
        print("Kata sandi kurang dari 10 karakter atau tidak sama.", file=sys.stderr)
        return 1
    with psycopg.connect(pengaturan().database_url, row_factory=dict_row) as conn:
        print("Guru dibuat, id:", buat_guru(conn, a.email, a.nama, sandi))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
