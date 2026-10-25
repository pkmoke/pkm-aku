"""Tes memakai Postgres sungguhan. Jalankan dengan:
   TEST_DATABASE_URL=postgresql://bemai_app:SANDI@127.0.0.1:5432/bemai pytest
(database sudah dimigrasi; lihat docker-compose.dev.yml). Tanpa variabel itu, tes dilewati."""
import os

import pytest

URL = os.environ.get("TEST_DATABASE_URL")
if URL:
    os.environ.update(DATABASE_URL=URL, COOKIE_SECURE="false", ASAL_DIIZINKAN="http://testserver")

pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL belum diisi")


def pytest_collection_modifyitems(config, items):
    if not URL:
        skip = pytest.mark.skip(reason="TEST_DATABASE_URL belum diisi")
        for it in items:
            it.add_marker(skip)


@pytest.fixture(scope="session", autouse=True)
def pool_db():
    if not URL:
        yield
        return
    from app.db import buka_pool, tutup_pool
    buka_pool()
    yield
    tutup_pool()


@pytest.fixture(scope="session")
def klien():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def db():
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(URL, row_factory=dict_row, autocommit=True) as conn:
        yield conn
        conn.execute("delete from pengguna where email like '%@uji.test' or nis like 'UJI%'")


@pytest.fixture()
def akun(db):
    """Guru dan dua siswa (VIII A, VII B). Semua sudah lewat tahap ganti sandi awal."""
    from app.akun import buat_guru, buat_siswa
    # Sisa akun uji dari jalannya tes yang terputus tidak boleh menggagalkan setup.
    db.execute("delete from pengguna where email like '%@uji.test' or nis like 'UJI%'")
    buat_guru(db, "guru@uji.test", "Guru Uji", "sandi-guru-uji")
    out = {"guru": ("guru@uji.test", "sandi-guru-uji")}
    for kunci, nis, tingkat, rombel in (("siswa", "UJI001", "VIII", "A"), ("siswa2", "UJI002", "VII", "B")):
        _, sandi = buat_siswa(db, nis, f"Siswa {nis}", tingkat, rombel)
        out[kunci] = (nis, sandi)
    db.execute("update pengguna set wajib_ganti_sandi = false where nis like 'UJI%'")
    return out
