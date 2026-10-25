from fastapi import APIRouter, Depends

from ..deps import butuh_peran
from ._stub import belum_dibuat

# Seluruh manajemen akun: guru saja. Pembuatan akun: lihat app/akun.py (buat_siswa).
router = APIRouter(tags=["siswa"], dependencies=[Depends(butuh_peran("guru"))])


@router.get("/kelas")
def kelas():
    belum_dibuat()


@router.get("/siswa")
def daftar(tingkat: str | None = None, rombel: str | None = None):
    belum_dibuat()


@router.post("/siswa")
def buat():
    belum_dibuat()


@router.post("/siswa/impor")
def impor():
    belum_dibuat()


@router.post("/siswa/{siswa_id}/reset-sandi")
def reset_sandi(siswa_id: str):
    """Set wajib_ganti_sandi = true dan hapus semua sesi siswa itu."""
    belum_dibuat()
