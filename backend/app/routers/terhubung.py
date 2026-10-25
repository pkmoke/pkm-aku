from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from ..layanan import materi_akses
from ..deps import butuh_peran
from ..db import koneksi
from ..deps import Pengguna,pengguna_aktif
from ..layanan import daftar_materi,daftar_soal,data_hasil
router=APIRouter(tags=['frontend'])

@router.get('/state')
def state(p:Pengguna=Depends(pengguna_aktif),conn=Depends(koneksi)):
    hasil=data_hasil(conn,p)
    sql="select * from chat where waktu>=now()-interval '24 hours'"
    args=[]
    if p.peran=='siswa': sql+=' and siswa_id=%s'; args.append(p.id)
    chat=[dict(waktu=int(r['waktu'].timestamp()*1000),tanya=r['pertanyaan'],kelas=r['kelas'])
          for r in conn.execute(sql+' order by waktu desc limit 100',args).fetchall()]
    aktivitas=[dict(waktu=h['waktu'],tipe='Latihan',judul='Materi '+str(h['materiId']),
                    hasil=str(h['nilai'])+'/100',kelas=h['kelas']) for h in hasil]
    aktivitas += [dict(waktu=c['waktu'],tipe='Chat',judul=c['tanya'],hasil='Selesai',kelas=c['kelas']) for c in chat]
    query="select * from aktivitas where waktu>=now()-interval '24 hours'"
    params=[]
    if p.peran=='siswa': query+=' and siswa_id=%s'; params.append(p.id)
    aktivitas += [dict(waktu=int(r['waktu'].timestamp()*1000),tipe=r['tipe'],judul=r['judul'],hasil=r['hasil'],kelas=r['kelas'])
                  for r in conn.execute(query+' order by waktu desc limit 100',params).fetchall()]
    aktivitas.sort(key=lambda x:x['waktu'],reverse=True)
    return dict(materi=daftar_materi(conn,p),soal=daftar_soal(conn,p),hasil=hasil,
                chat=chat,aktivitas=aktivitas[:100],dihapus=0)

class Rangkuman(BaseModel):
    materiId:int=Field(gt=0)

@router.post('/rangkuman',status_code=204)
def simpan_rangkuman(body:Rangkuman,p:Pengguna=Depends(butuh_peran('siswa')),conn=Depends(koneksi)):
    m=materi_akses(conn,p,body.materiId)
    conn.execute("insert into aktivitas(siswa_id,kelas,tipe,judul,hasil) values(%s,%s,'Rangkuman',%s,'Tersimpan')",(p.id,p.kelas,m['judul']))
