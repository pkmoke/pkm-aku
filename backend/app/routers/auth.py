"""Dua pintu login terpisah. Akun guru hanya bisa lewat /auth/login/guru, siswa lewat /auth/login/siswa.
Salah pintu, salah sandi, akun tak ada, dan akun terkunci semua dijawab SAMA (401) supaya tidak
membocorkan akun mana yang ada."""
import psycopg
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from ..config import pengaturan
from ..db import koneksi
from ..deps import Pengguna, catat_audit, sesi_pengguna
from ..galat import Galat
from ..security import buat_token, cek_sandi, hash_sandi, hash_token

router = APIRouter(prefix="/auth", tags=["auth"])
PESAN_LOGIN = "Identitas atau kata sandi salah"


class Login(BaseModel):
    identitas: str = Field(min_length=1, max_length=120)
    kataSandi: str = Field(min_length=1, max_length=200)


class GantiSandi(BaseModel):
    kataSandiLama: str = Field(min_length=1, max_length=200)
    kataSandiBaru: str = Field(min_length=8, max_length=200)


def pengguna_json(p: Pengguna) -> dict:
    d = {"id": p.id, "nama": p.nama, "peran": p.peran, "wajibGantiSandi": p.wajib_ganti_sandi}
    if p.peran == "siswa":
        d.update(nis=p.nis, kelas=p.kelas)
    return d


def _login(peran: str, body: Login, request: Request, response: Response, conn: psycopg.Connection):
    cfg = pengaturan()
    kondisi = "lower(email) = lower(%s)" if peran == "guru" else "nis = %s"
    row = conn.execute(
        f"""select id, nama, peran, nis, tingkat, rombel, wajib_ganti_sandi, kata_sandi_hash, gagal_login,
                   coalesce(terkunci_sampai > now(), false) as terkunci
            from pengguna where peran = %s and aktif and {kondisi}""",
        (peran, body.identitas.strip()),
    ).fetchone()

    # Selalu hitung hash (hash tiruan bila akun tak ada) agar waktu respons seragam.
    sandi_benar = cek_sandi(row["kata_sandi_hash"] if row else None, body.kataSandi)

    if not row or row["terkunci"] or not sandi_benar:
        if row and not row["terkunci"]:
            gagal = row["gagal_login"] + 1
            conn.execute(
                """update pengguna set gagal_login = %s,
                     terkunci_sampai = case when %s then now() + make_interval(mins => %s) else terkunci_sampai end
                   where id = %s""",
                (gagal, gagal >= cfg.maks_gagal_login, cfg.kunci_menit, row["id"]),
            )
        catat_audit(conn, f"login_gagal_{peran}", request, str(row["id"]) if row else None,
                    "terkunci" if row and row["terkunci"] else None)
        conn.commit()  # commit dulu: galat di bawah akan membuat dependency rollback
        raise Galat(401, "login_gagal", PESAN_LOGIN)

    token = buat_token()
    conn.execute("update pengguna set gagal_login = 0, terkunci_sampai = null where id = %s", (row["id"],))
    conn.execute(
        "insert into sesi (token_hash, pengguna_id, kedaluwarsa) values (%s, %s, now() + make_interval(hours => %s))",
        (hash_token(token), row["id"], cfg.sesi_jam),
    )
    catat_audit(conn, f"login_{peran}", request, str(row["id"]))
    response.set_cookie(cfg.cookie_nama, token, max_age=cfg.sesi_jam * 3600, httponly=True,
                        secure=cfg.cookie_secure, samesite="lax", path="/")
    p = Pengguna(id=str(row["id"]), nama=row["nama"], peran=row["peran"], nis=row["nis"],
                 tingkat=row["tingkat"], rombel=row["rombel"], wajib_ganti_sandi=row["wajib_ganti_sandi"])
    return {"pengguna": pengguna_json(p)}


@router.post("/login/guru")
def login_guru(body: Login, request: Request, response: Response, conn: psycopg.Connection = Depends(koneksi)):
    return _login("guru", body, request, response, conn)


@router.post("/login/siswa")
def login_siswa(body: Login, request: Request, response: Response, conn: psycopg.Connection = Depends(koneksi)):
    return _login("siswa", body, request, response, conn)


@router.get("/saya")
def saya(p: Pengguna = Depends(sesi_pengguna)):
    return {"pengguna": pengguna_json(p)}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, conn: psycopg.Connection = Depends(koneksi)):
    cfg = pengaturan()
    token = request.cookies.get(cfg.cookie_nama)
    if token:
        conn.execute("delete from sesi where token_hash = %s", (hash_token(token),))
    response.delete_cookie(cfg.cookie_nama, path="/")


@router.post("/ganti-sandi", status_code=204)
def ganti_sandi(body: GantiSandi, request: Request,
                p: Pengguna = Depends(sesi_pengguna), conn: psycopg.Connection = Depends(koneksi)):
    lama = conn.execute("select kata_sandi_hash from pengguna where id = %s", (p.id,)).fetchone()
    if not cek_sandi(lama["kata_sandi_hash"], body.kataSandiLama):
        raise Galat(400, "sandi_lama_salah", "Kata sandi lama tidak cocok")
    if body.kataSandiBaru == body.kataSandiLama:
        raise Galat(400, "sandi_sama", "Kata sandi baru harus berbeda")
    conn.execute("update pengguna set kata_sandi_hash = %s, wajib_ganti_sandi = false where id = %s",
                 (hash_sandi(body.kataSandiBaru), p.id))
    # Cabut semua sesi lain milik pengguna ini; sesi yang sedang dipakai tetap hidup.
    token = request.cookies.get(pengaturan().cookie_nama, "")
    conn.execute("delete from sesi where pengguna_id = %s and token_hash <> %s", (p.id, hash_token(token)))
    catat_audit(conn, "ganti_sandi", request, p.id)
