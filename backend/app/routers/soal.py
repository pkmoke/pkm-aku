from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field,model_validator
from ..deps import Pengguna,butuh_peran
from ..db import koneksi
from ..galat import Galat
from ..layanan import daftar_soal

baca=APIRouter(prefix='/soal',tags=['soal'],dependencies=[Depends(butuh_peran('guru','siswa'))])
tulis=APIRouter(prefix='/soal',tags=['soal'],dependencies=[Depends(butuh_peran('guru'))])

class Soal(BaseModel):
    materiId: int=Field(gt=0)
    topik: str=Field(default='Manual',max_length=100)
    tanya: str=Field(min_length=1,max_length=3000)
    opsi: list[str]=Field(min_length=2,max_length=8)
    jawaban: int=Field(ge=0)
    kelas: list[str]=Field(min_length=1,max_length=18)
    pembahasan: str=Field(default='',max_length=10000)

    @model_validator(mode='after')
    def valid(self):
        if self.jawaban>=len(self.opsi) or any(not x.strip() or len(x)>3000 for x in self.opsi):
            raise ValueError('Pilihan atau kunci tidak valid')
        return self

class Terbit(BaseModel):
    usulan:list[Soal]=Field(min_length=1,max_length=30)

def valid_materi(conn,s):
    m=conn.execute('select tingkat,rombel from materi where id=%s for update',(s.materiId,)).fetchone()
    if not m: raise Galat(404,'tidak_ada','Materi tidak ditemukan')
    if not set(s.kelas)<=set(m['tingkat']+' '+r for r in m['rombel']):
        raise Galat(400,'kelas_tidak_valid','Kelas soal harus termasuk kelas materi sumber')

def simpan_soal(conn,s,ident=None):
    valid_materi(conn,s)
    values=(s.materiId,s.topik,s.tanya,s.opsi,s.pembahasan,s.kelas)
    if ident is None:
        r=conn.execute('''insert into soal(materi_id,topik,tanya,opsi,pembahasan,kelas)
          values(%s,%s,%s,%s,%s,%s) returning id''',values).fetchone()
    else:
        r=conn.execute('''update soal set materi_id=%s,topik=%s,tanya=%s,opsi=%s,pembahasan=%s,kelas=%s
          where id=%s returning id''',values+(ident,)).fetchone()
        if not r: raise Galat(404,'tidak_ada','Soal tidak ditemukan')
    conn.execute('''insert into soal_kunci(soal_id,jawaban) values(%s,%s)
      on conflict(soal_id) do update set jawaban=excluded.jawaban''',(r['id'],s.jawaban))
    return dict(id=str(r['id']),**s.model_dump(exclude={'materiId'}),materiId=str(s.materiId))

@baca.get('')
def daftar(p:Pengguna=Depends(butuh_peran('guru','siswa')),conn=Depends(koneksi)):
    return daftar_soal(conn,p)

@tulis.post('')
def tambah(body:Soal,conn=Depends(koneksi)): return simpan_soal(conn,body)

@tulis.put('/{soal_id}')
def ubah(soal_id:int,body:Soal,conn=Depends(koneksi)): return simpan_soal(conn,body,soal_id)

@tulis.delete('/{soal_id}',status_code=204)
def hapus(soal_id:int,conn=Depends(koneksi)):
    if not conn.execute('delete from soal where id=%s returning id',(soal_id,)).fetchone():
        raise Galat(404,'tidak_ada','Soal tidak ditemukan')

@tulis.post('/terbitkan')
def terbitkan(body:Terbit,conn=Depends(koneksi)):
    return {'jumlah':len(body.usulan),'soal':[simpan_soal(conn,s) for s in body.usulan]}

@tulis.post('/generate')
def generate():
    raise Galat(501,'belum_dibuat','Gunakan generator definisi di frontend, lalu terbitkan untuk menyimpan')
