import pytest
from fastapi.testclient import TestClient

H = {"X-Requested-With": "bemai"}


def baru():
    from app.main import app
    return TestClient(app, base_url="http://testserver")


def masuk(peran, identitas, sandi):
    c = baru()
    r = c.post(f"/api/auth/login/{peran}", json={"identitas": identitas, "kataSandi": sandi}, headers=H)
    return c, r


# ---------------------------------------------------------------- pintu login terpisah
def test_pintu_login_benar_berhasil(akun):
    c, r = masuk("guru", *akun["guru"])
    assert r.status_code == 200 and r.json()["pengguna"]["peran"] == "guru"
    c, r = masuk("siswa", *akun["siswa"])
    assert r.status_code == 200
    p = r.json()["pengguna"]
    assert p["peran"] == "siswa" and p["kelas"] == "VIII A"


def test_guru_tidak_bisa_masuk_lewat_pintu_siswa_dan_sebaliknya(akun):
    _, r1 = masuk("siswa", *akun["guru"])   # email guru + sandi benar, pintu siswa
    _, r2 = masuk("guru", *akun["siswa"])  # NIS siswa + sandi benar, pintu guru
    assert r1.status_code == 401 and r2.status_code == 401


def test_semua_kegagalan_login_dijawab_sama(akun):
    """Salah pintu, salah sandi, akun tak ada: isi respons identik (tidak membocorkan akun)."""
    respons = [
        masuk("siswa", akun["guru"][0], akun["guru"][1])[1],       # salah pintu
        masuk("guru", akun["guru"][0], "salah-sandi")[1],          # salah sandi
        masuk("guru", "tidak-ada@uji.test", "apa-saja")[1],        # akun tak ada
    ]
    assert {r.status_code for r in respons} == {401}
    assert len({r.text for r in respons}) == 1


def test_cookie_sesi_httponly_samesite_dan_token_tidak_disimpan_polos(akun, db):
    c, r = masuk("guru", *akun["guru"])
    sc = r.headers["set-cookie"].lower()
    assert "httponly" in sc and "samesite=lax" in sc
    token = c.cookies.get("bemai_sesi")
    assert token and db.execute("select count(*) n from sesi where token_hash = %s", (token,)).fetchone()["n"] == 0


def test_akun_terkunci_setelah_gagal_berulang(akun):
    for _ in range(5):
        masuk("guru", akun["guru"][0], "salah")
    _, r = masuk("guru", *akun["guru"])  # sandi benar pun ditolak saat terkunci
    assert r.status_code == 401


# ---------------------------------------------------------------- matriks RBAC
ENDPOINT_GURU = [("GET", "/api/kelas"), ("GET", "/api/siswa"), ("POST", "/api/siswa"), ("POST", "/api/siswa/impor"),
                 ("POST", "/api/siswa/x/reset-sandi"), ("POST", "/api/materi"), ("PUT", "/api/materi/1"),
                 ("DELETE", "/api/materi/1"), ("POST", "/api/materi/unggah"), ("POST", "/api/soal"),
                 ("PUT", "/api/soal/1"), ("DELETE", "/api/soal/1"), ("POST", "/api/soal/generate"),
                 ("POST", "/api/soal/terbitkan"), ("GET", "/api/analisis"), ("DELETE", "/api/analisis"),
                 ("GET", "/api/dashboard")]
ENDPOINT_SISWA = [("POST", "/api/latihan"), ("POST", "/api/chat")]
ENDPOINT_KEDUANYA = [("GET", "/api/materi"), ("GET", "/api/materi/1"), ("GET", "/api/soal")]
SEMUA = ENDPOINT_GURU + ENDPOINT_SISWA + ENDPOINT_KEDUANYA


def panggil(c, m, u):
    return c.request(m, u, headers=H, json={} if m in ("POST", "PUT") else None)


@pytest.mark.parametrize("m,u", SEMUA)
def test_tanpa_login_ditolak_401(klien, m, u):
    assert panggil(baru(), m, u).status_code == 401


@pytest.mark.parametrize("m,u", ENDPOINT_GURU)
def test_siswa_ditolak_di_endpoint_guru(akun, m, u):
    c, _ = masuk("siswa", *akun["siswa"])
    assert panggil(c, m, u).status_code == 403


@pytest.mark.parametrize("m,u", ENDPOINT_SISWA)
def test_guru_ditolak_di_endpoint_siswa(akun, m, u):
    c, _ = masuk("guru", *akun["guru"])
    assert panggil(c, m, u).status_code == 403


@pytest.mark.parametrize("m,u", ENDPOINT_GURU + ENDPOINT_KEDUANYA)
def test_guru_lolos_penjaga(akun, m, u):
    c, _ = masuk("guru", *akun["guru"])
    assert panggil(c, m, u).status_code not in (401, 403)  # 501 sekarang; berubah saat diimplementasi


@pytest.mark.parametrize("m,u", ENDPOINT_SISWA + ENDPOINT_KEDUANYA)
def test_siswa_lolos_penjaga(akun, m, u):
    c, _ = masuk("siswa", *akun["siswa"])
    assert panggil(c, m, u).status_code not in (401, 403)


def test_kelas_siswa_dari_akun_bukan_dari_parameter():
    from app.deps import Pengguna, kelas_efektif
    siswa = Pengguna("1", "S", "siswa", "UJI001", "VIII", "A", False)
    guru = Pengguna("2", "G", "guru", None, None, None, False)
    assert kelas_efektif(siswa, "IX F") == "VIII A"      # siswa tidak bisa memilih kelas lain
    assert kelas_efektif(guru, "IX F") == "IX F"
    assert kelas_efektif(guru, None) is None


# ---------------------------------------------------------------- sesi
def test_wajib_ganti_sandi_memblokir_endpoint_lain(db):
    from app.akun import buat_siswa
    _, sandi = buat_siswa(db, "UJI009", "Baru", "IX", "C")
    c, r = masuk("siswa", "UJI009", sandi)
    assert r.json()["pengguna"]["wajibGantiSandi"] is True
    assert c.get("/api/auth/saya").status_code == 200
    blok = c.get("/api/materi")
    assert blok.status_code == 403 and blok.json()["error"]["kode"] == "wajib_ganti_sandi"
    ok = c.post("/api/auth/ganti-sandi", json={"kataSandiLama": sandi, "kataSandiBaru": "sandi-baru-123"}, headers=H)
    assert ok.status_code == 204
    assert c.get("/api/materi").status_code not in (401, 403)


def test_logout_mematikan_sesi(akun):
    c, _ = masuk("guru", *akun["guru"])
    assert c.get("/api/auth/saya").status_code == 200
    assert c.post("/api/auth/logout", headers=H).status_code == 204
    assert c.get("/api/auth/saya").status_code == 401


def test_akun_dinonaktifkan_langsung_kehilangan_akses(akun, db):
    c, _ = masuk("siswa", *akun["siswa"])
    assert c.get("/api/materi").status_code not in (401, 403)
    db.execute("update pengguna set aktif = false where nis = 'UJI001'")
    assert c.get("/api/materi").status_code == 401


def test_ganti_sandi_mencabut_sesi_lain(akun):
    c1, _ = masuk("guru", *akun["guru"])
    c2, _ = masuk("guru", *akun["guru"])
    r = c1.post("/api/auth/ganti-sandi", json={"kataSandiLama": akun["guru"][1], "kataSandiBaru": "sandi-baru-456"}, headers=H)
    assert r.status_code == 204
    assert c1.get("/api/auth/saya").status_code == 200
    assert c2.get("/api/auth/saya").status_code == 401


# ---------------------------------------------------------------- CSRF
def test_request_ubah_data_tanpa_header_kustom_ditolak(akun):
    c, _ = masuk("guru", *akun["guru"])
    r = c.post("/api/materi", json={})  # tanpa X-Requested-With
    assert r.status_code == 403 and r.json()["error"]["kode"] == "asal_tidak_valid"


def test_origin_asing_ditolak(akun):
    c, _ = masuk("guru", *akun["guru"])
    r = c.post("/api/materi", json={}, headers={**H, "Origin": "https://jahat.example"})
    assert r.status_code == 403
    r = c.post("/api/materi", json={}, headers={**H, "Origin": "http://testserver"})
    assert r.status_code not in (401, 403)


def test_health_publik_dan_galat_seragam(klien):
    assert klien.get("/api/health").json() == {"status": "ok"}
    r = klien.get("/api/tidak-ada")
    assert r.status_code == 404 and set(r.json()["error"]) == {"kode", "pesan"}
