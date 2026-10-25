from fastapi import APIRouter, Depends, Request, Response
import csv
import io

from ..db import koneksi
from ..deps import Pengguna, butuh_peran, catat_audit
from ..galat import Galat
from ..layanan import daftar_materi, daftar_soal, data_hasil

router = APIRouter(tags=["analisis"], dependencies=[Depends(butuh_peran("guru"))])

TINGKAT = ("VII", "VIII", "IX")
ROMBEL = ("A", "B", "C", "D", "E", "F")


def _lingkup(tingkat: str | None, rombel: str | None) -> list[str]:
    """Daftar kode kelas dari parameter, atau galat bila kosong/tidak dikenal.

    Dipakai untuk menghapus dan membaca rekap: tanpa lingkup, satu guru bisa
    menghapus data seluruh sekolah dalam satu permintaan.
    """
    if not tingkat:
        raise Galat(400, "lingkup_kurang", "Pilih tingkat kelas dulu (VII, VIII, atau IX)")
    if tingkat not in TINGKAT:
        raise Galat(400, "lingkup_tidak_valid", "Tingkat harus VII, VIII, atau IX")
    if rombel:
        if rombel not in ROMBEL:
            raise Galat(400, "lingkup_tidak_valid", "Rombel harus A sampai F")
        return [f"{tingkat} {rombel}"]
    return [f"{tingkat} {r}" for r in ROMBEL]


@router.get("/analisis")
def analisis(tingkat: str | None = None, rombel: str | None = None,
             p: Pengguna = Depends(butuh_peran("guru")), conn=Depends(koneksi)):
    hasil = data_hasil(conn, p)
    hasil = [h for h in hasil
             if (not tingkat or h["kelas"].split()[0] == tingkat)
             and (not rombel or h["kelas"].split()[1] == rombel)]
    return dict(hasil=hasil, jumlahLatihan=len(hasil),
                rataRata=round(sum(int(h["nilai"]) for h in hasil) / len(hasil)) if hasil else None)


@router.delete("/analisis")
def hapus_analisis(request: Request, tingkat: str | None = None, rombel: str | None = None,
                   p: Pengguna = Depends(butuh_peran("guru")), conn=Depends(koneksi)):
    """Hapus data analisis hanya untuk kelas yang dipilih, bukan seluruh sekolah."""
    kelas = _lingkup(tingkat, rombel)
    jumlah = {}
    for tabel in ("hasil", "aktivitas", "chat", "ringkasan_harian"):
        jumlah[tabel] = conn.execute(f"delete from {tabel} where kelas = any(%s)", (kelas,)).rowcount
    catat_audit(conn, "hapus_analisis", request, p.id, ", ".join(kelas))
    return dict(dihapus=jumlah, lingkup=kelas)


@router.get("/dashboard")
def dashboard(p: Pengguna = Depends(butuh_peran("guru")), conn=Depends(koneksi)):
    hasil = data_hasil(conn, p)
    return dict(materi=len(daftar_materi(conn, p)), soal=len(daftar_soal(conn, p)),
                latihan=len(hasil),
                rataRata=round(sum(int(h["nilai"]) for h in hasil) / len(hasil)) if hasil else 0)


@router.get("/rekap")
def rekap(tingkat: str | None = None, rombel: str | None = None, hari: int = 30,
          conn=Depends(koneksi)):
    """Rekap harian yang tetap ada setelah data 24 jam dibersihkan."""
    hari = max(1, min(hari, 365))
    sql = """select tanggal, kelas, jumlah_latihan, rata_rata from ringkasan_harian
             where tanggal >= current_date - %s"""
    args: list = [hari]
    if tingkat:
        sql += " and kelas = any(%s)"
        args.append(_lingkup(tingkat, rombel))
    rows = conn.execute(sql + " order by tanggal desc, kelas", args).fetchall()
    per, total = {}, 0
    for r in rows:
        total += r["jumlah_latihan"]
        a = per.setdefault(r["kelas"], dict(kelas=r["kelas"], latihan=0, nilai=0.0))
        a["latihan"] += r["jumlah_latihan"]
        a["nilai"] += float(r["rata_rata"] or 0) * r["jumlah_latihan"]
    per_kelas = [dict(kelas=v["kelas"], latihan=v["latihan"],
                      rataRata=round(v["nilai"] / v["latihan"], 1) if v["latihan"] else None)
                 for v in sorted(per.values(), key=lambda x: x["kelas"])]
    return dict(baris=[dict(tanggal=str(r["tanggal"]), kelas=r["kelas"],
                            jumlahLatihan=r["jumlah_latihan"],
                            rataRata=float(r["rata_rata"]) if r["rata_rata"] is not None else None)
                       for r in rows],
                perKelas=per_kelas, totalLatihan=total, hari=hari)


def _aman_csv(nilai) -> str:
    teks = "" if nilai is None else str(nilai)
    return "'" + teks if teks[:1] in ("=", "+", "-", "@") else teks


@router.get("/ekspor")
def ekspor(tingkat: str | None = None, rombel: str | None = None, conn=Depends(koneksi)):
    """Unduhan nilai 24 jam terakhir dalam CSV, bisa dibuka di Excel."""
    kelas = _lingkup(tingkat, rombel) if tingkat else [f"{t} {r}" for t in TINGKAT for r in ROMBEL]
    rows = conn.execute(
        """select h.waktu, p.nis, p.nama, h.kelas, m.judul, h.benar, h.total, h.nilai
           from hasil h
           left join pengguna p on p.id = h.siswa_id
           left join materi m on m.id = h.materi_id
           where h.kelas = any(%s) order by h.waktu desc""",
        (kelas,),
    ).fetchall()
    buf = io.StringIO()
    tulis = csv.writer(buf)
    tulis.writerow(["waktu", "nis", "nama", "kelas", "materi", "benar", "total", "nilai"])
    for r in rows:
        tulis.writerow([r["waktu"].isoformat(timespec="minutes"), _aman_csv(r["nis"]),
                        _aman_csv(r["nama"]), _aman_csv(r["kelas"]), _aman_csv(r["judul"]),
                        r["benar"], r["total"], r["nilai"]])
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="nilai-bemai.csv"'})
