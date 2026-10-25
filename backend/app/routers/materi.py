from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from ..deps import Pengguna, butuh_peran
from ..db import koneksi
from ..galat import Galat
from ..layanan import daftar_materi, materi_akses, materi_json

baca = APIRouter(prefix='/materi', tags=['materi'], dependencies=[Depends(butuh_peran('guru','siswa'))])
tulis = APIRouter(prefix='/materi', tags=['materi'], dependencies=[Depends(butuh_peran('guru'))])

class Materi(BaseModel):
    mapel: str = Field(min_length=1,max_length=100)
    kelas: Literal['VII','VIII','IX']
    rombel: list[Literal['A','B','C','D','E','F']] = Field(min_length=1,max_length=6)
    judul: str = Field(min_length=1,max_length=300)
    teks: list[str] = Field(min_length=1,max_length=500)
    rangkuman: list[str] = Field(default_factory=list,max_length=100)

    @field_validator('teks','rangkuman')
    @classmethod
    def batas_teks(cls, value):
        if sum(map(len,value)) > 200000:
            raise ValueError('Materi terlalu panjang')
        return value

@baca.get('')
def daftar(p: Pengguna=Depends(butuh_peran('guru','siswa')),conn=Depends(koneksi)):
    return daftar_materi(conn,p)

@baca.get('/{materi_id}')
def satu(materi_id:int,p:Pengguna=Depends(butuh_peran('guru','siswa')),conn=Depends(koneksi)):
    return materi_json(materi_akses(conn,p,materi_id))

@tulis.post('')
def tambah(body:Materi,conn=Depends(koneksi)):
    r=conn.execute('''insert into materi(mapel,tingkat,rombel,judul,teks,rangkuman)
        values(%s,%s,%s,%s,%s,%s) returning *''',
        (body.mapel,body.kelas,body.rombel,body.judul,body.teks,body.rangkuman)).fetchone()
    return materi_json(r)

@tulis.put('/{materi_id}')
def ubah(materi_id:int,body:Materi,conn=Depends(koneksi)):
    # Updating material must not silently strand already published questions.
    row=conn.execute('select id from materi where id=%s for update',(materi_id,)).fetchone()
    if not row: raise Galat(404,'tidak_ada','Materi tidak ditemukan')
    allowed=[body.kelas+' '+r for r in body.rombel]
    if conn.execute('select 1 from soal where materi_id=%s and not kelas <@ %s::text[] limit 1',
                    (materi_id,allowed)).fetchone():
        raise Galat(409,'kelas_soal','Sesuaikan kelas soal terkait sebelum mengubah kelas materi')
    r=conn.execute('''update materi set mapel=%s,tingkat=%s,rombel=%s,judul=%s,teks=%s,rangkuman=%s
        where id=%s returning *''',(body.mapel,body.kelas,body.rombel,body.judul,body.teks,body.rangkuman,materi_id)).fetchone()
    return materi_json(r)

@tulis.delete('/{materi_id}',status_code=204)
def hapus(materi_id:int,conn=Depends(koneksi)):
    if not conn.execute('delete from materi where id=%s returning id',(materi_id,)).fetchone():
        raise Galat(404,'tidak_ada','Materi tidak ditemukan')

@tulis.post('/unggah')
def unggah():
    raise Galat(501,'belum_dibuat','Ekstraksi PDF/DOCX belum tersedia; gunakan tempel teks')
