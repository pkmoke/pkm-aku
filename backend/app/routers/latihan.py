from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from psycopg.types.json import Jsonb
from ..db import koneksi
from ..deps import Pengguna,butuh_peran
from ..galat import Galat
from ..layanan import materi_akses,daftar_soal,hasil_json
router=APIRouter(tags=['latihan'],dependencies=[Depends(butuh_peran('siswa'))])
class Jawab(BaseModel):
    soalId:int=Field(gt=0)
    pilihan:int=Field(ge=-1,le=7)
class Latihan(BaseModel):
    materiId:int=Field(gt=0)
    jawaban:list[Jawab]=Field(min_length=1,max_length=200)
    ulangDari:int|None=Field(default=None,gt=0)

@router.post('/latihan')
def kumpulkan(body:Latihan,p:Pengguna=Depends(butuh_peran('siswa')),conn=Depends(koneksi)):
    materi_akses(conn,p,body.materiId)
    soal=daftar_soal(conn,p,body.materiId,kunci=True)
    expected={int(s['id']) for s in soal}
    if body.ulangDari:
        prev=conn.execute('select materi_id,detail from hasil where id=%s and siswa_id=%s',
                           (body.ulangDari,p.id)).fetchone()
        if not prev or prev['materi_id']!=body.materiId:
            raise Galat(404,'tidak_ada','Hasil latihan asal tidak ditemukan')
        expected &= {int(d['soalId']) for d in prev['detail'] if not d['benar']}
    received=[j.soalId for j in body.jawaban]
    if not expected or len(received)!=len(set(received)) or set(received)!=expected:
        raise Galat(400,'soal_tidak_valid','Kumpulkan tepat seluruh soal latihan yang tersedia')
    selected={j.soalId:j.pilihan for j in body.jawaban}
    detail=[]
    for s in soal:
        ident=int(s['id'])
        if ident not in expected: continue
        pilih=selected[ident]
        if pilih>=len(s['opsi']): raise Galat(400,'pilihan_tidak_valid','Pilihan di luar batas')
        detail.append(dict(soalId=s['id'],jawab=pilih,benar=pilih==s['jawaban'],kunci=s['jawaban'],
                           pembahasan=s.get('pembahasan') or ''))
    benar=sum(d['benar'] for d in detail)
    nilai=round(benar/len(detail)*100)
    row=conn.execute('''insert into hasil(siswa_id,materi_id,kelas,nilai,benar,total,detail,ulang_dari)
      values(%s,%s,%s,%s,%s,%s,%s,%s) returning *''',
      (p.id,body.materiId,p.kelas,nilai,benar,len(detail),Jsonb(detail),body.ulangDari)).fetchone()
    return hasil_json(row)
