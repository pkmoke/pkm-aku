import random
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from ..db import koneksi
from ..deps import Pengguna, butuh_peran
from ..galat import Galat
from ..layanan import daftar_soal, materi_akses

baca = APIRouter(prefix='/soal', tags=['soal'], dependencies=[Depends(butuh_peran('guru', 'siswa'))])
tulis = APIRouter(prefix='/soal', tags=['soal'], dependencies=[Depends(butuh_peran('guru'))])

POLA_DEFINISI = re.compile(r'^(.{3,70}?)\s+(adalah|yaitu|merupakan)\s+(.{5,})$', re.I)


class Soal(BaseModel):
    materiId: int = Field(gt=0)
    topik: str = Field(default='Manual', max_length=100)
    tanya: str = Field(min_length=1, max_length=3000)
    opsi: list[str] = Field(min_length=2, max_length=8)
    jawaban: int = Field(ge=0)
    kelas: list[str] = Field(min_length=1, max_length=18)
    pembahasan: str = Field(default='', max_length=10000)
    otomatis: bool = False

    @model_validator(mode='after')
    def valid(self):
        if self.jawaban >= len(self.opsi) or any(not x.strip() or len(x) > 3000 for x in self.opsi):
            raise ValueError('Pilihan atau kunci tidak valid')
        return self


class Terbit(BaseModel):
    usulan: list[Soal] = Field(min_length=1, max_length=30)


class Usulan(BaseModel):
    materiId: int = Field(gt=0)
    jumlah: int = Field(default=4, ge=2, le=8)


def valid_materi(conn, s):
    m = conn.execute('select tingkat,rombel from materi where id=%s for update', (s.materiId,)).fetchone()
    if not m:
        raise Galat(404, 'tidak_ada', 'Materi tidak ditemukan')
    if not set(s.kelas) <= set(m['tingkat'] + ' ' + r for r in m['rombel']):
        raise Galat(400, 'kelas_tidak_valid', 'Kelas soal harus termasuk kelas materi sumber')


def simpan_soal(conn, s, ident=None):
    valid_materi(conn, s)
    values = (s.materiId, s.topik, s.tanya, s.opsi, s.pembahasan, s.kelas, s.otomatis)
    if ident is None:
        r = conn.execute('''insert into soal(materi_id,topik,tanya,opsi,pembahasan,kelas,otomatis)
          values(%s,%s,%s,%s,%s,%s,%s) returning id''', values).fetchone()
    else:
        r = conn.execute('''update soal set materi_id=%s,topik=%s,tanya=%s,opsi=%s,pembahasan=%s,
          kelas=%s,otomatis=%s where id=%s returning id''', values + (ident,)).fetchone()
        if not r:
            raise Galat(404, 'tidak_ada', 'Soal tidak ditemukan')
    conn.execute('''insert into soal_kunci(soal_id,jawaban) values(%s,%s)
      on conflict(soal_id) do update set jawaban=excluded.jawaban''', (r['id'], s.jawaban))
    return dict(id=str(r['id']), **s.model_dump(exclude={'materiId'}), materiId=str(s.materiId))


def definisi(teks: list[str]) -> list[tuple[str, str]]:
    """Kalimat berpola "X adalah Y" dari materi, tanpa duplikat."""
    hasil = []
    for baris in teks:
        m = POLA_DEFINISI.match(baris.strip())
        if m:
            pasangan = (m.group(1).strip(), m.group(3).strip().rstrip('.'))
            if pasangan not in hasil:
                hasil.append(pasangan)
    return hasil


@baca.get('')
def daftar(p: Pengguna = Depends(butuh_peran('guru', 'siswa')), conn=Depends(koneksi)):
    return daftar_soal(conn, p)


@tulis.post('')
def tambah(body: Soal, conn=Depends(koneksi)):
    return simpan_soal(conn, body)


@tulis.put('/{soal_id}')
def ubah(soal_id: int, body: Soal, conn=Depends(koneksi)):
    return simpan_soal(conn, body, soal_id)


@tulis.delete('/{soal_id}', status_code=204)
def hapus(soal_id: int, conn=Depends(koneksi)):
    if not conn.execute('delete from soal where id=%s returning id', (soal_id,)).fetchone():
        raise Galat(404, 'tidak_ada', 'Soal tidak ditemukan')


@tulis.post('/terbitkan')
def terbitkan(body: Terbit, conn=Depends(koneksi)):
    return {'jumlah': len(body.usulan), 'soal': [simpan_soal(conn, s) for s in body.usulan]}


@tulis.post('/generate')
def generate(body: Usulan, p: Pengguna = Depends(butuh_peran('guru')), conn=Depends(koneksi)):
    """Draft soal definisi dari materi. Belum disimpan; guru tetap menekan terbitkan."""
    m = materi_akses(conn, p, body.materiId)
    pasangan = definisi(m['teks'])
    if len(pasangan) < 3:
        raise Galat(400, 'definisi_kurang',
                    'Materi ini belum punya cukup kalimat definisi (minimal 3 kalimat pola "X adalah Y")')
    acak = random.SystemRandom()
    dipilih = pasangan[:]
    acak.shuffle(dipilih)
    usulan = []
    for istilah, arti in dipilih[:min(body.jumlah, len(dipilih))]:
        salah = list(dict.fromkeys(a for i, a in pasangan if a != arti and i != istilah))
        acak.shuffle(salah)
        opsi = [arti] + salah[:3]
        acak.shuffle(opsi)
        usulan.append(dict(materiId=int(body.materiId), topik='Definisi', otomatis=True,
                           tanya=f'Apa yang dimaksud dengan {istilah}?', opsi=opsi,
                           jawaban=opsi.index(arti), pembahasan=f'{istilah} adalah {arti}'))
    return dict(usulan=usulan, jumlah=len(usulan), judul=m['judul'])
