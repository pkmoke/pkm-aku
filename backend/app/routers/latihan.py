import uuid

import psycopg
from fastapi import APIRouter, Depends
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from ..db import koneksi
from ..deps import Pengguna, butuh_peran
from ..galat import Galat
from ..layanan import daftar_soal, hasil_json, materi_akses

router = APIRouter(tags=["latihan"], dependencies=[Depends(butuh_peran("siswa"))])


class Jawab(BaseModel):
    soalId: int = Field(gt=0)
    pilihan: int = Field(ge=-1, le=7)


class Mulai(BaseModel):
    materiId: int = Field(gt=0)
    ulangDari: int | None = Field(default=None, gt=0)


class Latihan(BaseModel):
    materiId: int = Field(gt=0)
    jawaban: list[Jawab] = Field(min_length=1, max_length=200)
    sesiId: str | None = None
    kunci: str | None = Field(default=None, max_length=64)
    ulangDari: int | None = Field(default=None, gt=0)


def _hasil_milik(conn, p: Pengguna, ident: int):
    prev = conn.execute("select id, materi_id, detail from hasil where id = %s and siswa_id = %s",
                        (ident, p.id)).fetchone()
    if not prev:
        raise Galat(404, "tidak_ada", "Hasil latihan asal tidak ditemukan")
    return prev


def _salah(prev) -> set[int]:
    return {int(d["soalId"]) for d in prev["detail"] if not d["benar"]}


@router.post("/latihan/mulai")
def mulai(body: Mulai, p: Pengguna = Depends(butuh_peran("siswa")), conn=Depends(koneksi)):
    """Kunci daftar soal untuk satu percobaan.

    Daftar soal dibekukan di sini supaya perubahan guru di tengah latihan tidak
    membuat jawaban siswa ditolak saat dikumpulkan.
    """
    materi = materi_akses(conn, p, body.materiId)
    # Sesi yang ditinggal tidak dibiarkan menumpuk; tujuh hari cukup untuk satu percobaan.
    conn.execute("delete from latihan_sesi where siswa_id = %s and dibuat < now() - interval '7 days'",
                 (p.id,))
    soal = daftar_soal(conn, p, body.materiId)
    izin = {int(s["id"]) for s in soal}
    if body.ulangDari:
        prev = _hasil_milik(conn, p, body.ulangDari)
        if prev["materi_id"] != body.materiId:
            raise Galat(404, "tidak_ada", "Hasil latihan asal tidak ditemukan")
        izin &= _salah(prev)
    dipilih = [s for s in soal if int(s["id"]) in izin]
    if not dipilih:
        raise Galat(400, "soal_kosong", "Belum ada soal untuk materi ini")
    row = conn.execute(
        """insert into latihan_sesi (siswa_id, materi_id, soal_ids, ulang_dari)
           values (%s, %s, %s, %s) returning id""",
        (p.id, body.materiId, [int(s["id"]) for s in dipilih], body.ulangDari),
    ).fetchone()
    return dict(sesiId=str(row["id"]), materiId=str(materi["id"]), judul=materi["judul"],
                mapel=materi["mapel"], soal=dipilih,
                ulangDari=str(body.ulangDari) if body.ulangDari else None)


@router.post("/latihan")
def kumpulkan(body: Latihan, p: Pengguna = Depends(butuh_peran("siswa")), conn=Depends(koneksi)):
    if body.kunci:
        ada = conn.execute("select * from hasil where siswa_id = %s and kunci = %s",
                           (p.id, body.kunci)).fetchone()
        if ada:
            return hasil_json(ada)

    materi_akses(conn, p, body.materiId)
    soal = daftar_soal(conn, p, body.materiId, kunci=True)
    asal = body.ulangDari
    sesi = None
    if body.sesiId:
        try:
            uuid.UUID(body.sesiId)
        except ValueError:
            raise Galat(400, "sesi_tidak_valid", "Nomor sesi latihan tidak valid")
        sesi = conn.execute(
            "select * from latihan_sesi where id = %s and siswa_id = %s for update",
            (body.sesiId, p.id)).fetchone()
        if not sesi:
            raise Galat(404, "sesi_tidak_ada", "Sesi latihan tidak ditemukan")
        if sesi["materi_id"] != body.materiId:
            raise Galat(400, "sesi_tidak_cocok", "Sesi ini bukan untuk materi tersebut")
        if sesi["dipakai"]:
            raise Galat(409, "sesi_dipakai", "Sesi latihan ini sudah dikumpulkan")
        asal = sesi["ulang_dari"]
        izin = {int(x) for x in sesi["soal_ids"]}
        soal = [s for s in soal if int(s["id"]) in izin]
        if not soal:
            raise Galat(409, "sesi_kosong", "Soal pada sesi ini sudah tidak tersedia")

    expected = {int(s["id"]) for s in soal}
    if asal:
        prev = _hasil_milik(conn, p, asal)
        if prev["materi_id"] != body.materiId:
            raise Galat(404, "tidak_ada", "Hasil latihan asal tidak ditemukan")
        expected &= _salah(prev)

    received = [j.soalId for j in body.jawaban]
    if not expected or len(received) != len(set(received)) or set(received) != expected:
        raise Galat(400, "soal_tidak_valid", "Kumpulkan tepat seluruh soal latihan yang tersedia")

    selected = {j.soalId: j.pilihan for j in body.jawaban}
    detail = []
    for s in soal:
        ident = int(s["id"])
        if ident not in expected:
            continue
        pilih = selected[ident]
        if pilih >= len(s["opsi"]):
            raise Galat(400, "pilihan_tidak_valid", "Pilihan di luar batas")
        detail.append(dict(soalId=s["id"], jawab=pilih, benar=pilih == s["jawaban"],
                           kunci=s["jawaban"], pembahasan=s.get("pembahasan") or ""))

    benar = sum(1 for d in detail if d["benar"])
    nilai = round(benar / len(detail) * 100)
    nilai_kolom = "siswa_id,materi_id,kelas,nilai,benar,total,detail,ulang_dari,kunci"
    try:
        with conn.transaction():
            row = conn.execute(
                f"""insert into hasil ({nilai_kolom}) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    returning *""",
                (p.id, body.materiId, p.kelas, nilai, benar, len(detail), Jsonb(detail), asal,
                 body.kunci),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        # Permintaan kembar (tombol diklik dua kali / jaringan mengulang) memakai hasil yang sama.
        row = conn.execute("select * from hasil where siswa_id = %s and kunci = %s",
                           (p.id, body.kunci)).fetchone()
        if sesi:
            conn.execute("update latihan_sesi set dipakai = now() where id = %s", (sesi["id"],))
        return hasil_json(row)
    if sesi:
        conn.execute("update latihan_sesi set dipakai = now() where id = %s", (sesi["id"],))
    return hasil_json(row)
