from fastapi import APIRouter,Depends
from ..db import koneksi
from ..deps import Pengguna,butuh_peran,catat_audit
from ..layanan import data_hasil,daftar_materi,daftar_soal
from fastapi import Request
router=APIRouter(tags=['analisis'],dependencies=[Depends(butuh_peran('guru'))])
@router.get('/analisis')
def analisis(tingkat:str|None=None,rombel:str|None=None,p:Pengguna=Depends(butuh_peran('guru')),conn=Depends(koneksi)):
    hasil=data_hasil(conn,p)
    hasil=[h for h in hasil if (not tingkat or h['kelas'].split()[0]==tingkat) and (not rombel or h['kelas'].split()[1]==rombel)]
    return dict(hasil=hasil,jumlahLatihan=len(hasil),rataRata=round(sum(h['nilai'] for h in hasil)/len(hasil)) if hasil else None)
@router.delete('/analisis',status_code=204)
def hapus_analisis(request:Request,p:Pengguna=Depends(butuh_peran('guru')),conn=Depends(koneksi)):
    for table in ('hasil','aktivitas','chat','ringkasan_harian'):
        conn.execute('delete from '+table) # table names are fixed server constants
    catat_audit(conn,'hapus_analisis',request,p.id)
@router.get('/dashboard')
def dashboard(p:Pengguna=Depends(butuh_peran('guru')),conn=Depends(koneksi)):
    hasil=data_hasil(conn,p)
    return dict(materi=len(daftar_materi(conn,p)),soal=len(daftar_soal(conn,p)),latihan=len(hasil),
                rataRata=round(sum(h['nilai'] for h in hasil)/len(hasil)) if hasil else 0)
