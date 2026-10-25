from typing import Literal
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..deps import Pengguna, butuh_peran, catat_audit
from ..db import koneksi
from ..galat import Galat
from ..security import hash_sandi, sandi_awal

# Seluruh manajemen akun: guru saja. Siswa tidak punya akses ke sini.
router = APIRouter(tags=["siswa"], dependencies=[Depends(butuh_peran("guru"))])

TINGKAT = ("VII", "VIII", "IX")
ROMBEL = ("A", "B", "C", "D", "E", "F")


class SiswaBaru(BaseModel):
    nis: str = Field(min_length=1, max_length=30)
    nama: str = Field(min_length=1, max_length=120)
    tingkat: Literal["VII", "VIII", "IX"]
    rombel: Literal["A", "B", "C", "D", "E", "F"]


class BarisImpor(BaseModel):
    nis: str = Field(min_length=1, max_length=200)
    nama: str = Field(default="", max_length=2000)
    tingkat: Literal["VII", "VIII", "IX"]
    rombel: Literal["A", "B", "C", "D", "E", "F"]


class StatusSiswa(BaseModel):
    aktif: bool


class ImporSiswa(BaseModel):
    baris: list[BarisImpor] = Field(min_length=1, max_length=300)


def siswa_json(r) -> dict:
    return dict(id=str(r["id"]), nis=r["nis"], nama=r["nama"], tingkat=r["tingkat"],
                rombel=r["rombel"], kelas=f"{r['tingkat']} {r['rombel']}",
                aktif=r["aktif"], wajibGantiSandi=r["wajib_ganti_sandi"])


@router.get("/kelas")
def kelas(conn=Depends(koneksi)):
    """Semua kelas VII-IX A-F beserta jumlah siswa aktif, termasuk kelas yang masih kosong."""
    angka = {(r["tingkat"], r["rombel"]): r["jumlah"] for r in conn.execute(
        """select tingkat, rombel, count(*) filter (where aktif) as jumlah
           from pengguna where peran = 'siswa' group by 1, 2""").fetchall()}
    isi, total = [], 0
    for t in TINGKAT:
        for r in ROMBEL:
            n = angka.get((t, r), 0)
            total += n
            isi.append(dict(tingkat=t, rombel=r, kelas=f"{t} {r}", siswa=n))
    return dict(kelas=isi, total=total)


@router.get("/siswa")
def daftar(tingkat: str | None = None, rombel: str | None = None, cari: str | None = None,
           conn=Depends(koneksi)):
    sql = """select id, nis, nama, tingkat, rombel, aktif, wajib_ganti_sandi
             from pengguna where peran = 'siswa'"""
    args = []
    if tingkat:
        sql += " and tingkat = %s"
        args.append(tingkat)
    if rombel:
        sql += " and rombel = %s"
        args.append(rombel)
    if cari and cari.strip():
        sql += " and (nis ilike %s or nama ilike %s)"
        args.extend([f"%{cari.strip()}%", f"%{cari.strip()}%"])
    rows = conn.execute(sql + " order by tingkat, rombel, nama limit 500", args).fetchall()
    return [siswa_json(r) for r in rows]


@router.post("/siswa", status_code=201)
def buat(body: SiswaBaru, request: Request, p: Pengguna = Depends(butuh_peran("guru")),
         conn=Depends(koneksi)):
    """Satu akun siswa baru. Kata sandi awal hanya muncul di respons ini."""
    nis = body.nis.strip()
    if not nis or not body.nama.strip():
        raise Galat(400, "data_tidak_valid", "NIS dan nama wajib diisi")
    sandi = sandi_awal()
    row = conn.execute(
        """insert into pengguna (peran, nama, nis, tingkat, rombel, kata_sandi_hash)
           values ('siswa', %s, %s, %s, %s, %s)
           on conflict (nis) do nothing
           returning id, nis, nama, tingkat, rombel, aktif, wajib_ganti_sandi""",
        (body.nama.strip(), nis, body.tingkat, body.rombel, hash_sandi(sandi)),
    ).fetchone()
    if not row:
        raise Galat(409, "nis_dipakai", f"NIS {nis} sudah dipakai akun lain")
    catat_audit(conn, "buat_siswa", request, p.id, nis)
    return dict(siswa=siswa_json(row), kataSandiAwal=sandi)


@router.post("/siswa/impor")
def impor(body: ImporSiswa, request: Request, p: Pengguna = Depends(butuh_peran("guru")),
          conn=Depends(koneksi)):
    """Impor banyak siswa sekaligus. Baris yang gagal dilaporkan satu per satu, tidak membatalkan sisanya."""
    dibuat, gagal, dipakai = [], [], set()
    for baris in body.baris:
        nis = baris.nis.strip()
        nama = baris.nama.strip()
        if not nis or not nama:
            gagal.append(dict(nis=nis, alasan="NIS dan nama wajib diisi"))
            continue
        if len(nis) > 30:
            gagal.append(dict(nis=nis[:30], alasan="NIS lebih dari 30 karakter"))
            continue
        if len(nama) > 120:
            gagal.append(dict(nis=nis, alasan="Nama lebih dari 120 karakter"))
            continue
        if nis in dipakai:
            gagal.append(dict(nis=nis, alasan="NIS ganda di dalam daftar impor"))
            continue
        sandi = sandi_awal()
        row = conn.execute(
            """insert into pengguna (peran, nama, nis, tingkat, rombel, kata_sandi_hash)
               values ('siswa', %s, %s, %s, %s, %s)
               on conflict (nis) do nothing
               returning id, nis, nama, tingkat, rombel, aktif, wajib_ganti_sandi""",
            (nama, nis, baris.tingkat, baris.rombel, hash_sandi(sandi)),
        ).fetchone()
        if not row:
            gagal.append(dict(nis=nis, alasan="NIS sudah dipakai akun lain"))
            continue
        dipakai.add(nis)
        dibuat.append(dict(**siswa_json(row), kataSandiAwal=sandi))
    catat_audit(conn, "impor_siswa", request, p.id, f"{len(dibuat)} dibuat, {len(gagal)} gagal")
    return dict(dibuat=dibuat, gagal=gagal, jumlah=len(dibuat))


@router.post("/siswa/{siswa_id}/reset-sandi")
def reset_sandi(siswa_id: str, request: Request, p: Pengguna = Depends(butuh_peran("guru")),
                conn=Depends(koneksi)):
    """Sandi awal baru, wajib diganti saat login, dan semua sesi siswa itu dicabut."""
    try:
        uuid.UUID(siswa_id)
    except ValueError:
        raise Galat(404, "tidak_ada", "Akun siswa tidak ditemukan")
    row = conn.execute("select id, nis, nama from pengguna where id = %s and peran = 'siswa'",
                       (siswa_id,)).fetchone()
    if not row:
        raise Galat(404, "tidak_ada", "Akun siswa tidak ditemukan")
    sandi = sandi_awal()
    conn.execute("""update pengguna set kata_sandi_hash = %s, wajib_ganti_sandi = true,
                    gagal_login = 0, terkunci_sampai = null where id = %s""",
                 (hash_sandi(sandi), row["id"]))
    conn.execute("delete from sesi where pengguna_id = %s", (row["id"],))
    catat_audit(conn, "reset_sandi_siswa", request, p.id, row["nis"])
    return dict(kataSandiAwal=sandi, siswa=dict(id=str(row["id"]), nis=row["nis"], nama=row["nama"]))


@router.patch("/siswa/{siswa_id}/status")
def ubah_status(siswa_id: str, body: StatusSiswa, request: Request,
                p: Pengguna = Depends(butuh_peran("guru")), conn=Depends(koneksi)):
    """Menonaktifkan akun tanpa menghapus riwayatnya; sesi yang berjalan ikut dicabut."""
    try:
        uuid.UUID(siswa_id)
    except ValueError:
        raise Galat(404, "tidak_ada", "Akun siswa tidak ditemukan")
    row = conn.execute(
        """update pengguna set aktif = %s where id = %s and peran = 'siswa'
           returning id, nis, nama, tingkat, rombel, aktif, wajib_ganti_sandi""",
        (body.aktif, siswa_id)).fetchone()
    if not row:
        raise Galat(404, "tidak_ada", "Akun siswa tidak ditemukan")
    if not body.aktif:
        conn.execute("delete from sesi where pengguna_id = %s", (row["id"],))
    catat_audit(conn, "aktif_siswa" if body.aktif else "nonaktif_siswa", request, p.id, row["nis"])
    return siswa_json(row)
