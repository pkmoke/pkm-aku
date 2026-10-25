# pkm-aku — Bemai, aplikasi pembelajaran terhubung

Frontend ES modules, backend FastAPI, dan PostgreSQL. Login, sesi, materi, soal,
penilaian, latihan ulang, chat, rangkuman yang disimpan, riwayat dan analisis kini
menggunakan API. localStorage tidak dipakai sebagai database atau sumber hak akses.

## Clone repository

```sh
git clone https://github.com/pkmoke/pkm-aku.git
cd pkm-aku
```

Panduan lengkap: [menjalankan aplikasi](docs/menjalankan.md) ·
[clone, pull, push, dan kolaborasi](docs/kolaborasi.md) · [kontrak API](docs/api.md).

## Menjalankan

### Docker lokal

```sh
docker compose -f docker-compose.dev.yml up --build
```

Buka http://127.0.0.1:8081. Volume kosong diinisialisasi dengan migrasi dan seed.
Buat guru melalui CLI; tidak ada pendaftaran guru publik:

```sh
docker compose -f docker-compose.dev.yml exec api python -m app.cli buat-guru --email guru@sekolah.sch.id --nama 'Nama Guru'
```

Database yang sudah ada perlu menerapkan migrasi baru `0004_aktivitas_siswa.sql`
sebagai admin. Jangan menerapkan ulang seluruh migrasi pada database yang sudah berisi skema.

### Tanpa Docker / tunnel ngrok

Siapkan PostgreSQL, jalankan `db/role-app.sql`, migrasi berurutan, dan `db/seed.sql`
pada database baru. Isi `backend/.env` dari `.env.example`.

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.local:app --host 127.0.0.1 --port 8899
```

`app.local` melayani frontend dan `/api` pada port yang sama. Untuk HTTPS ngrok,
pakai `COOKIE_SECURE=true` dan masukkan URL HTTPS tunnel ke `ASAL_DIIZINKAN`.
Untuk akses HTTP localhost gunakan `COOKIE_SECURE=false` hanya pada lingkungan lokal.
`app.main` tetap menjadi entrypoint container API dengan frontend nginx terpisah.

Jangan lagi memakai `python -m http.server` sebagai aplikasi lengkap: itu hanya server
file dan tidak menyediakan `/api`.

## Alur dan batas keamanan

- Guru masuk dengan email; siswa masuk dengan NIS. Kelas dan peran diambil dari akun server.
- Siswa baru wajib mengganti sandi awal sebelum menerima data pembelajaran.
- Cookie sesi HttpOnly; token disimpan sebagai hash di database; logout mencabut sesi.
- Materi/soal siswa difilter kelas di server. Kunci dan pembahasan tidak ada pada daftar soal siswa.
- Server menghitung nilai; field nilai/benar dari client tidak dijadikan sumber kebenaran.
- Submit normal harus memuat seluruh soal yang tersedia; retry hanya soal salah dari hasil milik siswa tersebut.
- Tujuan soal harus termasuk kelas materi sumber. Perubahan kelas materi yang membuat soal tidak konsisten ditolak.
- Riwayat hasil/chat/aktivitas dipisahkan berdasarkan ID siswa. Filter waktu 24 jam diterapkan ketika membaca data.
- Pembersihan fisik/rekap retensi memerlukan penjadwalan `db/pg_cron.sql`; PostgreSQL lokal tidak otomatis mempunyai pg_cron.
- Data seed jawaban tidak disajikan oleh entrypoint lokal atau nginx.

Ini lingkungan pengujian, bukan pernyataan semua temuan audit selesai. Temuan login
paralel, kebijakan lockout dan throttling ganti sandi masih perlu diperbaiki; server lokal
terintegrasi juga belum mempunyai rate limit nginx. Jangan gunakan akun/data sekolah nyata dahulu.

## Belum tersedia

- LLM eksternal: chat masih pencarian teks materi, dijalankan di server.
- Ekstraksi PDF/DOCX; input TXT/MD atau tempel teks dapat disimpan sebagai materi.
- Endpoint pengelolaan/impor/reset siswa masih 501; akun uji dibuat melalui setup lokal.
- `/soal/generate` server masih 501; generator definisi frontend membuat draft, lalu
  `/soal/terbitkan` memvalidasi dan menyimpannya.
- Snapshot soal pada server dan idempotensi submit belum tersedia. Bila guru mengubah soal
  saat latihan berlangsung, server menilai versi yang berlaku saat pengumpulan.

## Pengujian

```sh
cd backend
TEST_DATABASE_URL='postgresql://bemai_app:...@127.0.0.1:55432/bemai_test' python -m pytest -q
```

Gunakan database test terpisah yang sudah dimigrasi. Tes mencakup autentikasi, RBAC,
penyaringan kelas, ownership riwayat, kunci soal, nilai client palsu, retry dan validasi publikasi.

`audit/integration_http.py` dan `audit/integration_browser.py` adalah pemeriksaan sesi
pengujian lokal dengan akun disposable yang tersimpan di `/private/tmp/bemai-runtime.json`.
Tes frontend lama `tests/rendering.cjs` dan `tests/learning.cjs` dibuat untuk mode demo
localStorage dan tidak menggambarkan kontrak aplikasi terhubung.

Laporan audit sebelum penyambungan: `audit/REVIEW.md` dan `audit/API-REVIEW.md`.
Catatan `audit/CONNECTED.md` hanya tersedia lokal karena berisi kredensial pengujian.
Untuk setup mesin baru gunakan [panduan menjalankan](docs/menjalankan.md).
