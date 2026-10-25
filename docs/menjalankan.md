# Menjalankan Bemai dari repository

Kode: [github.com/pkmoke/pkm-aku](https://github.com/pkmoke/pkm-aku).
Aplikasi memerlukan FastAPI dan PostgreSQL; frontend berupa HTML/CSS/ES modules tanpa
build npm. Jalur tercepat untuk rekan baru adalah Docker Compose di bawah.

## Pilihan A — Docker Compose (disarankan)

### Persyaratan

- Git.
- Docker Desktop atau Docker Engine dengan Compose v2; Docker harus sedang berjalan.
- Port localhost 8081 (web) dan 55432 (database) tersedia.

Periksa instalasi:

```sh
git --version
docker --version
docker compose version
```

### 1. Clone dan jalankan

```sh
git clone https://github.com/pkmoke/pkm-aku.git
cd pkm-aku
docker compose -f docker-compose.dev.yml up -d --build
```

File compose pengembangan berdiri sendiri. Jangan menggabungkannya dengan
`docker-compose.yml` produksi. Docker membuat database, role aplikasi, skema, dan seed
5 materi/9 soal ketika volume database masih kosong. Akun login tidak dibuat oleh seed.
Tidak perlu menyalin `.env` laptop pemilik; konfigurasi dev ada pada compose.
Password dev dalam compose hanya untuk localhost, bukan untuk deployment publik.

### 2. Periksa layanan

```sh
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs --tail=80 db api web
curl http://127.0.0.1:8081/api/health
```

Respons health yang diharapkan: `{"status":"ok"}`. Tunggu database selesai inisialisasi
jika build pertama masih berlangsung. Gunakan alamat **http://127.0.0.1:8081**, sesuai
Origin yang diizinkan. Penggunaan `http://localhost:8081` perlu ditambahkan tersendiri
ke `ASAL_DIIZINKAN` jika diinginkan.

### 3. Buat akun guru

```sh
docker compose -f docker-compose.dev.yml exec api python -m app.cli buat-guru --email guru@example.com --nama "Guru Penguji"
```

Masukkan kata sandi minimal 10 karakter dua kali ketika diminta. Sandi tidak ditulis
ke argumen command atau source. Buka web, pilih **Guru**, lalu login dengan akun itu.
Tidak tersedia pendaftaran guru publik.

### 4. Buat akun siswa untuk pengujian

Cara normal: login guru, buka **Kelola Siswa**, lalu buat satu akun atau tempel daftar
kelas (format `NIS,Nama` per baris). Sandi awal hanya muncul sekali.

Untuk membuat akun lewat terminal (misalnya sebelum frontend terbaru terpasang):

```sh
docker compose -f docker-compose.dev.yml exec api python -c "import psycopg; from psycopg.rows import dict_row; from app.config import pengaturan; from app.akun import buat_siswa; conn=psycopg.connect(pengaturan().database_url, row_factory=dict_row); ident,sandi=buat_siswa(conn, 'UJI8A', 'Siswa Penguji', 'VIII', 'A'); conn.commit(); conn.close(); print('ID:',ident); print('Sandi awal:',sandi)"
```

Simpan sandi awal yang tampil. Pada web pilih **Siswa**, isi NIS `UJI8A` dan sandi awal,
lalu selesaikan modal ganti kata sandi. Kelas VIII A berasal dari akun server. Gunakan
NIS berbeda bila membuat akun tambahan; NIS harus unik.

### 5. Uji alur lengkap

1. Login guru; tambahkan materi dan soal untuk VIII A.
2. Buka browser/profile lain, login siswa VIII A dan kerjakan latihan.
3. Nilai dihitung server. Lihat riwayat siswa dan analisis guru; muat ulang halaman
   atau buka ulang menu untuk mengambil perubahan terbaru.
4. Coba akun siswa kelas lain untuk memastikan materi VIII A tidak terlihat.
5. Logout, lalu periksa bahwa sesi tidak dapat dipakai kembali.

Gunakan data fiktif; pekerjaan penyambungan belum menutup semua temuan audit keamanan.

### 6. Menghentikan dan memperbarui

```sh
# Menghentikan container; data volume tetap tersimpan.
docker compose -f docker-compose.dev.yml down

# Mengambil kode terbaru lalu menjalankan kembali.
git pull --ff-only origin main
docker compose -f docker-compose.dev.yml up -d --build
```

Jika ada migrasi baru dan volume sudah berisi database, jalankan hanya migrasi baru
sebagai admin. Migrasi awal tidak dijalankan ulang otomatis. Contoh untuk volume versi
lama yang belum mempunyai sesi latihan dan kolom idempotensi:

```sh
docker compose -f docker-compose.dev.yml exec db psql -U postgres -d bemai -v ON_ERROR_STOP=1 -f /db/migrations/0005_sesi_latihan.sql
```

Migrasi `0005_sesi_latihan.sql` aman diulang (semua perintahnya idempoten), tetapi
migrasi lama tidak: proyek ini belum memiliki runner/version table. `down -v` menghapus volume beserta seluruh akun dan hasil;
hindari opsi tersebut bila data masih diperlukan.

## Pilihan B — Python dan PostgreSQL tanpa Docker

### 1. Siapkan runtime dan database baru

Pasang Python 3.12+ dan PostgreSQL 16. Pastikan perintah `python3`, `psql`, dan `createdb`
tersedia (di Windows Python dapat bernama `python`). PostgreSQL harus berjalan.
Gunakan database baru khusus proyek, bukan database aplikasi lain.

Dari root repository pada shell POSIX (macOS/Linux):

```sh
createdb bemai
# -U admin_database dapat ditambahkan bila user database berbeda dengan user OS.
psql -d bemai -v ON_ERROR_STOP=1 -v sandi='contoh-sandi-backend-lokal' -f db/role-app.sql
for f in db/migrations/*.sql; do psql -d bemai -v ON_ERROR_STOP=1 -f "$f" || break; done
psql -d bemai -v ON_ERROR_STOP=1 -f db/seed.sql
```

Ganti contoh sandi dengan sandi lokal Anda dan gunakan nilai yang sama pada URL koneksi.
Jalankan perintah ini sebagai admin database yang memiliki izin membuat role dan tabel.
Jangan lanjut ke seed jika salah satu migrasi gagal. Perintah di atas untuk database
kosong; jangan mengulang migrasi awal pada database yang sudah memiliki tabel.

### 2. Virtualenv dan konfigurasi

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Pada Windows PowerShell, aktifkan dengan `.\.venv\Scripts\Activate.ps1` dan gunakan
`Copy-Item .env.example .env` untuk menyalin contoh. Untuk inisialisasi SQL, jalankan
file migrasi berurutan dengan `psql` atau gunakan jalur Docker.

Edit `backend/.env` untuk HTTP lokal:

```dotenv
DATABASE_URL=postgresql://bemai_app:contoh-sandi-backend-lokal@127.0.0.1:5432/bemai
ASAL_DIIZINKAN=http://127.0.0.1:8899
COOKIE_SECURE=false
DOCS_AKTIF=false
```

Sesuaikan port PostgreSQL. Jika sandi mengandung karakter khusus URL, gunakan URL
encoding pada bagian password. `.env` diabaikan Git dan harus dibuat sendiri oleh
masing-masing pengembang.

### 3. Jalankan frontend dan backend pada port yang sama

Tetap dari `backend/` dengan virtualenv aktif:

```sh
python -m app.cli buat-guru --email guru@example.com --nama "Guru Penguji"
python -m uvicorn app.local:app --host 127.0.0.1 --port 8899
```

Buka **http://127.0.0.1:8899**; health di `/api/health`. Entry point `app.local` melayani
frontend dan API sehingga tidak memerlukan CORS atau proxy tambahan. `app.main` hanya
melayani API dan digunakan container bersama frontend nginx.

Untuk membuat siswa, jalankan perintah helper pada bagian Docker tanpa awalan
`docker compose ... exec api`, dari terminal lain di `backend/` dengan virtualenv aktif.

## Pengujian backend dengan database terpisah

Tes menulis/menghapus akun dan data uji. Siapkan `bemai_test` terpisah, terapkan migrasi
serta seed menggunakan akun admin. Jangan menunjuk database berisi data pengguna nyata.
Jika role `bemai_app` sudah dibuat di server PostgreSQL yang sama, tidak perlu membuat
ulang role untuk database test.

Contoh setup menggunakan database Docker yang sedang berjalan, dari root repository:

```sh
docker compose -f docker-compose.dev.yml exec db createdb -U postgres bemai_test
docker compose -f docker-compose.dev.yml exec db sh -c 'for f in /db/migrations/*.sql; do psql -U postgres -d bemai_test -v ON_ERROR_STOP=1 -f "$f" || exit 1; done'
docker compose -f docker-compose.dev.yml exec db psql -U postgres -d bemai_test -v ON_ERROR_STOP=1 -f /db/seed.sql
```

Di mesin host, gunakan virtualenv Python dengan `requirements-dev.txt`, lalu:

```sh
cd backend
TEST_DATABASE_URL='postgresql://bemai_app:dev-sandi-lokal@127.0.0.1:55432/bemai_test' python -m pytest -q
```

PowerShell menggunakan `$env:TEST_DATABASE_URL = 'postgresql://...'` lalu
`python -m pytest -q`. Tanpa variabel ini, tes database dilewati.

Suite memuat autentikasi, sesi, RBAC, isolasi kelas/akun, penyembunyian kunci soal,
penilaian server, retry dan validasi publikasi. Script `audit/integration_*.py` merekam
pengujian ngrok sesi pengembangan sebelumnya dan memerlukan file runtime lokal yang
sengaja tidak ikut repository; gunakan suite pytest untuk pengujian yang portabel.

## Mengakses lewat ngrok

Pada setup tanpa Docker, jalankan tunnel ke port 8899; pada Docker gunakan port 8081.
Autentikasi ngrok di mesin sendiri tanpa mengirim token lewat chat atau menyimpannya
ke repository. Setelah mendapat URL HTTPS, tambahkan URL itu ke `ASAL_DIIZINKAN`,
set `COOKIE_SECURE=true`, dan restart API. Origin harus tepat sesuai URL browser.

```sh
# Tanpa Docker
ngrok http http://127.0.0.1:8899

# Alternatif Docker (jalankan hanya salah satu)
ngrok http http://127.0.0.1:8081
```

Pada Docker, ubah environment dev pada mesin lokal untuk pengujian HTTPS dan buat ulang
service api. Jangan memakai credential dev untuk deployment publik produksi.

## Pemecahan masalah

| Gejala | Pemeriksaan |
|---|---|
| `port is already allocated` | Hentikan layanan milik proyek yang memakai port itu, atau sesuaikan port compose/URL/Origin secara konsisten. |
| `/api/health` berupa HTML 404 | Kemungkinan memakai server statis; gunakan Compose atau `app.local:app`. |
| 502 dari nginx saat awal startup | Periksa `logs api db`, tunggu database siap dan pastikan migrasi berhasil. |
| 403 `asal_tidak_valid` | Samakan Origin browser dan `ASAL_DIIZINKAN`; client mutasi memerlukan header kustom. |
| Login sukses tetapi request berikutnya 401 | Pada HTTP lokal `COOKIE_SECURE` harus false; HTTPS publik true. Jangan mencampur hostname/IP. |
| NIS/email sudah ada | Gunakan identitas unik atau login dengan akun yang sudah dibuat. |
| 403 `wajib_ganti_sandi` | Selesaikan ganti sandi awal di web. |
| 400 saat menerbitkan soal | Kelas soal harus termasuk kelas materi sumber. |
| API 501 | Hanya ekstraksi dokumen (`/materi/unggah`) yang masih kerangka; bukan kesalahan login. |

## Batas fitur dan produksi

Chat menggunakan pencarian teks di server, belum LLM. Ekstraksi PDF/DOCX belum tersedia.
Akun siswa, impor, reset sandi, rekap 30 hari, dan unduhan CSV sudah tersedia. Masih
terbuka: kepemilikan materi/soal per guru dan rate limit nginx pada server lokal. `db/pg_cron.sql` digunakan pada PostgreSQL yang mempunyai
pg_cron; lokal tidak otomatis menjadwalkan pembersihan fisik meskipun pembacaan riwayat
sudah memakai filter 24 jam. Lihat [laporan audit](../audit/REVIEW.md) dan
[panduan deploy](deploy.md) sebelum merencanakan produksi.
