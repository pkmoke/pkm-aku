import re
from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from ..db import koneksi
from ..deps import Pengguna,butuh_peran
from ..layanan import daftar_materi
router=APIRouter(tags=['chat'],dependencies=[Depends(butuh_peran('siswa'))])
class Tanya(BaseModel):
    pertanyaan:str=Field(min_length=1,max_length=2000)
@router.post('/chat')
def tanya(body:Tanya,p:Pengguna=Depends(butuh_peran('siswa')),conn=Depends(koneksi)):
    stop={'apa','itu','yang','dan','dari','pada','adalah','jelaskan','tentang','dengan'}
    kata={k for k in re.findall(r'\w+',body.pertanyaan.lower()) if len(k)>2 and k not in stop}
    candidates=[]
    for m in daftar_materi(conn,p):
        for teks in m['teks']:
            score=sum(k in teks.lower() for k in kata)
            if score: candidates.append((score,teks,m))
    candidates.sort(key=lambda x:x[0],reverse=True)
    m=candidates[0][2] if candidates else None
    jawaban='\n'.join(c[1] for c in candidates if c[2]['id']==m['id'])[:6000] if m else None
    conn.execute('insert into chat(siswa_id,kelas,pertanyaan,jawaban,materi_id) values(%s,%s,%s,%s,%s)',
                 (p.id,p.kelas,body.pertanyaan,jawaban,int(m['id']) if m else None))
    return dict(jawaban=jawaban,alasan=None if jawaban else 'tidak_ada_materi',
                sumber=dict(materiId=m['id'],judul=m['judul']) if m else None)
