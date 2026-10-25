"""Regression tests against real PostgreSQL, alongside the existing auth matrix."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

H={'X-Requested-With':'bemai'}

def login(pair,role):
    c=TestClient(app)
    r=c.post('/api/auth/login/'+role,headers=H,json={'identitas':pair[0],'kataSandi':pair[1]})
    assert r.status_code==200
    return c

@pytest.fixture
def data_uji(db,akun):
    t=login(akun['guru'],'guru')
    a=login(akun['siswa'],'siswa')
    b=login(akun['siswa2'],'siswa')
    r=t.post('/api/materi',headers=H,json={'mapel':'IPA','kelas':'VIII','rombel':['A'],
                'judul':'Integrasi otomatis','teks':['Integrasi adalah penyambungan dua bagian.']})
    assert r.status_code==200
    m=r.json()
    q={'materiId':m['id'],'tanya':'Apa itu integrasi?','opsi':['Penyambungan','Pemutusan'],'jawaban':0,'kelas':['VIII A']}
    r=t.post('/api/soal',headers=H,json=q)
    assert r.status_code==200
    s=r.json()
    yield t,a,b,m,s,q
    db.execute('delete from hasil where materi_id=%s',(int(m['id']),))
    db.execute('delete from chat where materi_id=%s',(int(m['id']),))
    db.execute('delete from materi where id=%s',(int(m['id']),))
    for c in (t,a,b): c.close()

def test_kunci_tidak_ada_di_daftar_siswa(data_uji):
    _,a,_,_,_,_=data_uji
    for s in a.get('/api/soal').json():
        assert 'jawaban' not in s and 'pembahasan' not in s
    assert all('jawaban' not in s for s in a.get('/api/state').json()['soal'])

def test_objek_lintas_kelas_tidak_bisa_dibaca_atau_dikumpulkan(data_uji):
    _,_,b,m,s,_=data_uji
    assert b.get('/api/materi/'+m['id']).status_code==404
    assert b.post('/api/latihan',headers=H,json={'materiId':m['id'],'jawaban':[{'soalId':s['id'],'pilihan':0}]}).status_code==404

def test_nilai_client_diabaikan_dan_riwayat_isolasi(data_uji):
    _,a,b,m,s,_=data_uji
    r=a.post('/api/latihan',headers=H,json={'materiId':m['id'],'nilai':100,'jawaban':[{'soalId':s['id'],'pilihan':1}]})
    assert r.status_code==200
    h=r.json()
    assert h['nilai']==0 and h['detail'][0]['kunci']==0
    assert any(x['id']==h['id'] for x in a.get('/api/state').json()['hasil'])
    assert all(x['id']!=h['id'] for x in b.get('/api/state').json()['hasil'])

def test_duplikat_soal_dan_pilihan_di_luar_batas_ditolak(data_uji):
    _,a,_,m,s,_=data_uji
    for jawaban in [[{'soalId':s['id'],'pilihan':0}]*2,[{'soalId':s['id'],'pilihan':7}]]:
        assert a.post('/api/latihan',headers=H,json={'materiId':m['id'],'jawaban':jawaban}).status_code==400

def test_ulang_hanya_soal_salah_dan_milik_sendiri(data_uji):
    _,a,b,m,s,_=data_uji
    def submit(c,choice,asal=None):
        return c.post('/api/latihan',headers=H,json={'materiId':m['id'],'ulangDari':asal,'jawaban':[{'soalId':s['id'],'pilihan':choice}]})
    h=submit(a,1).json()
    r=submit(a,0,h['id'])
    assert r.status_code==200 and r.json()['nilai']==100
    assert submit(b,0,h['id']).status_code==404
    assert submit(a,0,r.json()['id']).status_code==400

def test_terbit_lintas_kelas_ditolak_dan_edit_tidak_merusak_kelas_soal(data_uji):
    t,_,_,m,_,q=data_uji
    assert t.post('/api/soal',headers=H,json={**q,'kelas':['VII B']}).status_code==400
    assert t.put('/api/materi/'+m['id'],headers=H,json={**m,'kelas':'VII','rombel':['B']}).status_code==409

def test_chat_server_menggunakan_materi_kelas(data_uji):
    _,a,b,m,_,_=data_uji
    r=a.post('/api/chat',headers=H,json={'pertanyaan':'Apa itu integrasi?'})
    assert r.status_code==200 and r.json()['sumber']['materiId']==m['id']
    r=b.post('/api/chat',headers=H,json={'pertanyaan':'Apa itu integrasi?'})
    assert r.status_code==200 and r.json()['jawaban'] is None

def test_riwayat_siswa_sekelas_tetap_terpisah(data_uji,db):
    from app.akun import buat_siswa
    _,a,_,m,s,_=data_uji
    ident,sandi=buat_siswa(db,'UJI003','Siswa Sekelas','VIII','A')
    db.execute('update pengguna set wajib_ganti_sandi=false where id=%s',(ident,))
    other=login(('UJI003',sandi),'siswa')
    try:
        h=a.post('/api/latihan',headers=H,json={'materiId':m['id'],'jawaban':[{'soalId':s['id'],'pilihan':0}]}).json()
        assert a.post('/api/rangkuman',headers=H,json={'materiId':m['id']}).status_code==204
        assert any(x['tipe']=='Rangkuman' and x['judul']==m['judul'] for x in a.get('/api/state').json()['aktivitas'])
        state=other.get('/api/state').json()
        assert all(x['id']!=h['id'] for x in state['hasil'])
        assert all(x['judul']!=m['judul'] for x in state['aktivitas'])
    finally:
        other.close()
