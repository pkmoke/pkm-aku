"""Pemetaan database dan batas akses bersama untuk frontend terhubung."""
from .galat import Galat


def materi_json(r):
    return dict(id=str(r['id']), mapel=r['mapel'], kelas=r['tingkat'], rombel=r['rombel'],
                judul=r['judul'], teks=r['teks'], rangkuman=r['rangkuman'])


def daftar_materi(conn, p):
    if p.peran == 'guru':
        rows = conn.execute('select * from materi order by id').fetchall()
    else:
        rows = conn.execute('select * from materi where tingkat=%s and %s=any(rombel) order by id',
                            (p.tingkat, p.rombel)).fetchall()
    return [materi_json(r) for r in rows]


def materi_akses(conn, p, ident):
    row = conn.execute('select * from materi where id=%s', (ident,)).fetchone()
    if not row or (p.peran == 'siswa' and (row['tingkat'] != p.tingkat or p.rombel not in row['rombel'])):
        raise Galat(404, 'tidak_ada', 'Materi tidak ditemukan')
    return row


def daftar_soal(conn, p, materi_id=None, kunci=False):
    # Student keys are selected ONLY for grading on the server, never in the public list.
    sql = '''select s.*, k.jawaban from soal s join soal_kunci k on k.soal_id=s.id
             join materi m on m.id=s.materi_id where true'''
    args = []
    if p.peran == 'siswa':
        sql += ' and %s=any(s.kelas) and m.tingkat=%s and %s=any(m.rombel)'
        args.extend([p.kelas, p.tingkat, p.rombel])
    if materi_id is not None:
        sql += ' and s.materi_id=%s'
        args.append(materi_id)
    rows = conn.execute(sql + ' order by s.id', args).fetchall()
    out = []
    for r in rows:
        s = dict(id=str(r['id']), materiId=str(r['materi_id']), topik=r['topik'],
                 tanya=r['tanya'], opsi=r['opsi'], kelas=r['kelas'])
        if p.peran == 'guru' or kunci:
            s.update(jawaban=r['jawaban'], pembahasan=r['pembahasan'])
        out.append(s)
    return out


def hasil_json(r):
    return dict(id=str(r['id']), materiId=str(r['materi_id']) if r['materi_id'] else None,
                waktu=int(r['waktu'].timestamp()*1000), kelas=r['kelas'], nilai=r['nilai'],
                benar=r['benar'], total=r['total'], detail=r['detail'],
                ulangDari=str(r['ulang_dari']) if r['ulang_dari'] else None)


def data_hasil(conn, p):
    sql = "select * from hasil where waktu >= now()-interval '24 hours'"
    args = []
    if p.peran == 'siswa':
        sql += ' and siswa_id=%s'
        args.append(p.id)
    return [hasil_json(r) for r in conn.execute(sql+' order by waktu desc', args).fetchall()]
