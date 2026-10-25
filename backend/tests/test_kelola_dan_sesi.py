"""Manajemen akun siswa, hapus analisis berlingkup, sesi latihan, dan generator soal."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

H = {'X-Requested-With': 'bemai'}


def login(pair, role):
    c = TestClient(app)
    r = c.post('/api/auth/login/' + role, headers=H,
               json={'identitas': pair[0], 'kataSandi': pair[1]})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture
def guru(akun):
    return login(akun['guru'], 'guru')


def siswa_baru(guru, nis, nama, tingkat, rombel):
    r = guru.post('/api/siswa', headers=H,
                  json={'nis': nis, 'nama': nama, 'tingkat': tingkat, 'rombel': rombel})
    assert r.status_code == 201, r.text
    return r.json()


def materi_dan_soal(guru, rombel=('A',), kelas=('VIII A',)):
    m = guru.post('/api/materi', headers=H, json={
        'mapel': 'IPA', 'kelas': 'VIII', 'rombel': list(rombel),
        'judul': 'Materi kelola uji',
        'teks': ['Respirasi adalah proses pengambilan oksigen oleh sel.',
                 'Alveolus adalah tempat pertukaran gas di paru-paru.',
                 'Diafragma adalah otot yang membantu pernapasan.'],
    }).json()
    s = guru.post('/api/soal', headers=H, json={
        'materiId': m['id'], 'tanya': 'Tempat pertukaran gas?',
        'opsi': ['Alveolus', 'Trakea'], 'jawaban': 0, 'kelas': list(kelas)}).json()
    return m, s


def test_kelas_dan_daftar_siswa(guru):
    k = guru.get('/api/kelas').json()
    assert len(k['kelas']) == 18
    kode = {(x['tingkat'], x['rombel']): x for x in k['kelas']}
    assert kode[('VIII', 'A')]['kelas'] == 'VIII A'
    daftar = guru.get('/api/siswa?tingkat=VIII&rombel=A').json()
    assert isinstance(daftar, list)
    assert all(x['kelas'] == 'VIII A' for x in daftar)


def test_buat_siswa_mendapat_sandi_awal_dan_wajib_ganti(guru):
    data = siswa_baru(guru, 'UJI101', 'Siswa Baru', 'VIII', 'C')
    assert data['siswa']['kelas'] == 'VIII C'
    assert len(data['kataSandiAwal']) == 10
    c = login(('UJI101', data['kataSandiAwal']), 'siswa')
    try:
        assert c.get('/api/state').status_code == 403
        assert c.get('/api/auth/saya').json()['pengguna']['wajibGantiSandi'] is True
    finally:
        c.close()


def test_nis_ganda_ditolak(guru):
    siswa_baru(guru, 'UJI102', 'Pertama', 'VIII', 'C')
    r = guru.post('/api/siswa', headers=H,
                  json={'nis': 'UJI102', 'nama': 'Kedua', 'tingkat': 'VIII', 'rombel': 'D'})
    assert r.status_code == 409 and r.json()['error']['kode'] == 'nis_dipakai'


def test_impor_melaporkan_baris_gagal(guru):
    siswa_baru(guru, 'UJI103', 'Sudah Ada', 'VIII', 'C')
    r = guru.post('/api/siswa/impor', headers=H, json={'baris': [
        {'nis': 'UJI104', 'nama': 'Impor Satu', 'tingkat': 'VIII', 'rombel': 'C'},
        {'nis': 'UJI103', 'nama': 'Duplikat', 'tingkat': 'VIII', 'rombel': 'C'},
        {'nis': 'UJI104', 'nama': 'Ganda Dalam Daftar', 'tingkat': 'VIII', 'rombel': 'D'},
    ]})
    assert r.status_code == 200
    data = r.json()
    assert data['jumlah'] == 1
    assert len(data['gagal']) == 2


def test_reset_sandi_mencabut_sesi_lama(guru):
    data = siswa_baru(guru, 'UJI105', 'Siswa Reset', 'VIII', 'C')
    lama = login(('UJI105', data['kataSandiAwal']), 'siswa')
    assert lama.get('/api/auth/saya').status_code == 200
    r = guru.post(f"/api/siswa/{data['siswa']['id']}/reset-sandi", headers=H)
    assert r.status_code == 200
    sandi_baru = r.json()['kataSandiAwal']
    assert sandi_baru != data['kataSandiAwal']
    assert lama.get('/api/auth/saya').status_code == 401
    lama.close()
    baru = login(('UJI105', sandi_baru), 'siswa')
    baru.close()


def test_siswa_tidak_boleh_kelola_akun(akun):
    c = login(akun['siswa'], 'siswa')
    try:
        assert c.get('/api/siswa').status_code == 403
        assert c.post('/api/siswa', headers=H, json={
            'nis': 'UJI999', 'nama': 'Nakal', 'tingkat': 'VIII', 'rombel': 'A'}).status_code == 403
    finally:
        c.close()


def test_hapus_analisis_wajib_lingkup_dan_tidak_menyapu_kelas_lain(guru, db):
    a = siswa_baru(guru, 'UJI106', 'Siswa A', 'VIII', 'A')
    b = siswa_baru(guru, 'UJI107', 'Siswa B', 'VII', 'B')
    db.execute("update pengguna set wajib_ganti_sandi = false where nis in ('UJI106','UJI107')")
    ca = login(('UJI106', a['kataSandiAwal']), 'siswa')
    cb = login(('UJI107', b['kataSandiAwal']), 'siswa')

    m, s = materi_dan_soal(guru, rombel=('A',), kelas=('VIII A',))
    m7 = guru.post('/api/materi', headers=H, json={
        'mapel': 'IPA', 'kelas': 'VII', 'rombel': ['B'], 'judul': 'Materi VII B',
        'teks': ['Bilangan prima adalah bilangan yang hanya punya dua faktor.']}).json()
    s7 = guru.post('/api/soal', headers=H, json={
        'materiId': m7['id'], 'tanya': 'Bilangan prima?',
        'opsi': ['Dua faktor', 'Tiga faktor'], 'jawaban': 0, 'kelas': ['VII B']}).json()

    assert ca.post('/api/latihan', headers=H, json={
        'materiId': m['id'], 'jawaban': [{'soalId': s['id'], 'pilihan': 0}]}).status_code == 200
    assert cb.post('/api/latihan', headers=H, json={
        'materiId': m7['id'], 'jawaban': [{'soalId': s7['id'], 'pilihan': 0}]}).status_code == 200

    assert guru.delete('/api/analisis', headers=H).status_code == 400
    kosong = guru.delete('/api/analisis?tingkat=IX', headers=H)
    assert kosong.status_code == 200 and kosong.json()['dihapus']['hasil'] == 0

    hasil = guru.delete('/api/analisis?tingkat=VIII&rombel=A', headers=H)
    assert hasil.status_code == 200
    assert hasil.json()['dihapus']['hasil'] >= 1
    sisa_a = ca.get('/api/state').json()['hasil']
    sisa_b = cb.get('/api/state').json()['hasil']
    assert sisa_a == []
    assert len(sisa_b) == 1
    for c in (ca, cb):
        c.close()
    db.execute('delete from hasil where siswa_id in (%s, %s)',
               (a['siswa']['id'], b['siswa']['id']))
    db.execute('delete from materi where id in (%s, %s)', (int(m['id']), int(m7['id'])))


def test_sesi_latihan_membekukan_soal(guru, akun):
    c = login(akun['siswa'], 'siswa')
    m, s = materi_dan_soal(guru, rombel=('A',), kelas=('VIII A',))
    try:
        mulai = c.post('/api/latihan/mulai', headers=H, json={'materiId': m['id']})
        assert mulai.status_code == 200
        sesi = mulai.json()
        assert [x['id'] for x in sesi['soal']] == [s['id']]

        tambahan = guru.post('/api/soal', headers=H, json={
            'materiId': m['id'], 'tanya': 'Soal menyusul?',
            'opsi': ['Ya', 'Tidak'], 'jawaban': 0, 'kelas': ['VIII A']}).json()
        assert tambahan['id']

        r = c.post('/api/latihan', headers=H, json={
            'materiId': m['id'], 'sesiId': sesi['sesiId'],
            'jawaban': [{'soalId': s['id'], 'pilihan': 0}]})
        assert r.status_code == 200, r.text
        assert r.json()['nilai'] == 100

        ulang = c.post('/api/latihan', headers=H, json={
            'materiId': m['id'], 'sesiId': sesi['sesiId'],
            'jawaban': [{'soalId': s['id'], 'pilihan': 0}]})
        assert ulang.status_code == 409 and ulang.json()['error']['kode'] == 'sesi_dipakai'
    finally:
        c.close()
        guru.delete('/api/materi/' + m['id'], headers=H)


def test_submit_kembar_tidak_menggandakan_nilai(guru, akun):
    c = login(akun['siswa'], 'siswa')
    m, s = materi_dan_soal(guru, rombel=('A',), kelas=('VIII A',))
    body = {'materiId': m['id'], 'kunci': 'kunci-uji-1',
            'jawaban': [{'soalId': s['id'], 'pilihan': 0}]}
    try:
        satu = c.post('/api/latihan', headers=H, json=body)
        dua = c.post('/api/latihan', headers=H, json=body)
        assert satu.status_code == 200 and dua.status_code == 200
        assert satu.json()['id'] == dua.json()['id']
        ids = [h['id'] for h in c.get('/api/state').json()['hasil']]
        assert ids.count(satu.json()['id']) == 1
    finally:
        c.close()
        guru.delete('/api/materi/' + m['id'], headers=H)


def test_generate_soal_dari_materi(guru):
    m, _ = materi_dan_soal(guru)
    r = guru.post('/api/soal/generate', headers=H, json={'materiId': m['id'], 'jumlah': 3})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['usulan'] and all(x['otomatis'] for x in data['usulan'])
    for s in data['usulan']:
        assert 0 <= s['jawaban'] < len(s['opsi'])
        assert ' adalah ' in s['pembahasan']
    guru.delete('/api/materi/' + m['id'], headers=H)


def test_generate_ditolak_kalau_definisi_kurang(guru):
    m = guru.post('/api/materi', headers=H, json={
        'mapel': 'IPS', 'kelas': 'VIII', 'rombel': ['A'], 'judul': 'Materi tipis',
        'teks': ['Satu kalimat saja tanpa pola definisi.']}).json()
    try:
        r = guru.post('/api/soal/generate', headers=H, json={'materiId': m['id']})
        assert r.status_code == 400 and r.json()['error']['kode'] == 'definisi_kurang'
    finally:
        guru.delete('/api/materi/' + m['id'], headers=H)


def test_rekap_harian_bertahan_setelah_retensi(guru, db):
    data = siswa_baru(guru, 'UJI120', 'Siswa Rekap', 'VIII', 'A')
    db.execute("update pengguna set wajib_ganti_sandi = false where id = %s", (data['siswa']['id'],))
    db.execute("""insert into hasil (siswa_id, kelas, nilai, benar, total, detail, waktu)
                  values (%s, 'VIII A', 80, 4, 5, '[]'::jsonb, now() - interval '2 days')""",
               (data['siswa']['id'],))
    db.execute("select * from jalankan_retensi()")
    r = guru.get('/api/rekap?tingkat=VIII&rombel=A&hari=30')
    assert r.status_code == 200
    body = r.json()
    assert body['perKelas'] and body['perKelas'][0]['kelas'] == 'VIII A'
    assert body['perKelas'][0]['latihan'] >= 1
    assert body['totalLatihan'] >= 1


def test_ekspor_nilai_csv(guru, akun):
    c = login(akun['siswa'], 'siswa')
    m, s = materi_dan_soal(guru, rombel=('A',), kelas=('VIII A',))
    try:
        c.post('/api/latihan', headers=H, json={
            'materiId': m['id'], 'jawaban': [{'soalId': s['id'], 'pilihan': 0}]})
        r = guru.get('/api/ekspor?tingkat=VIII&rombel=A')
        assert r.status_code == 200
        assert r.headers['content-type'].startswith('text/csv')
        assert 'attachment' in r.headers['content-disposition']
        baris = r.text.strip().splitlines()
        assert baris[0] == 'waktu,nis,nama,kelas,materi,benar,total,nilai'
        assert any('UJI001' in b and 'VIII A' in b for b in baris[1:])
    finally:
        c.close()
        guru.delete('/api/materi/' + m['id'], headers=H)


def test_ganti_sandi_dibatasi_setelah_lima_kegagalan(guru):
    data = siswa_baru(guru, 'UJI121', 'Siswa Ganti', 'VIII', 'C')
    db_sandi = data['kataSandiAwal']
    c = login(('UJI121', db_sandi), 'siswa')
    c.post('/api/auth/ganti-sandi', headers=H,
           json={'kataSandiLama': 'salah-salah', 'kataSandiBaru': 'sandi-baru-123'})
    try:
        for _ in range(4):
            r = c.post('/api/auth/ganti-sandi', headers=H,
                       json={'kataSandiLama': 'salah-salah', 'kataSandiBaru': 'sandi-baru-123'})
            assert r.status_code == 400
        r = c.post('/api/auth/ganti-sandi', headers=H,
                   json={'kataSandiLama': 'salah-salah', 'kataSandiBaru': 'sandi-baru-123'})
        assert r.status_code == 429 and r.json()['error']['kode'] == 'terlalu_banyak'
        benar = c.post('/api/auth/ganti-sandi', headers=H,
                       json={'kataSandiLama': db_sandi, 'kataSandiBaru': 'sandi-baru-123'})
        assert benar.status_code == 429
    finally:
        c.close()


def test_hitungan_gagal_login_direset_setelah_masa_kunci(guru, db):
    data = siswa_baru(guru, 'UJI122', 'Siswa Kunci', 'VIII', 'C')
    for _ in range(5):
        r = TestClient(app).post('/api/auth/login/siswa', headers=H,
                                 json={'identitas': 'UJI122', 'kataSandi': 'salah'})
        assert r.status_code == 401
    db.execute("update pengguna set terkunci_sampai = now() - interval '1 minute' where nis = 'UJI122'")
    r = TestClient(app).post('/api/auth/login/siswa', headers=H,
                             json={'identitas': 'UJI122', 'kataSandi': 'salah'})
    assert r.status_code == 401
    sisa = db.execute("select gagal_login, terkunci_sampai from pengguna where nis = 'UJI122'").fetchone()
    assert sisa['gagal_login'] == 1 and sisa['terkunci_sampai'] is None
    ok = TestClient(app).post('/api/auth/login/siswa', headers=H,
                              json={'identitas': 'UJI122', 'kataSandi': data['kataSandiAwal']})
    assert ok.status_code == 200


def test_nonaktifkan_akun_mencabut_akses(guru):
    data = siswa_baru(guru, 'UJI123', 'Siswa Status', 'VIII', 'C')
    c = login(('UJI123', data['kataSandiAwal']), 'siswa')
    try:
        assert c.get('/api/auth/saya').status_code == 200
        r = guru.patch(f"/api/siswa/{data['siswa']['id']}/status", headers=H, json={'aktif': False})
        assert r.status_code == 200 and r.json()['aktif'] is False
        assert c.get('/api/auth/saya').status_code == 401
        masuk = TestClient(app).post('/api/auth/login/siswa', headers=H,
                                     json={'identitas': 'UJI123', 'kataSandi': data['kataSandiAwal']})
        assert masuk.status_code == 401
        hidup = guru.patch(f"/api/siswa/{data['siswa']['id']}/status", headers=H, json={'aktif': True})
        assert hidup.status_code == 200 and hidup.json()['aktif'] is True
        lagi = TestClient(app).post('/api/auth/login/siswa', headers=H,
                                    json={'identitas': 'UJI123', 'kataSandi': data['kataSandiAwal']})
        assert lagi.status_code == 200
    finally:
        c.close()
