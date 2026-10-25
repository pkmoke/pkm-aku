# API terhubung

Prefix `/api`; cookie sesi HttpOnly. Request perubahan data memerlukan
`X-Requested-With: bemai`; Origin yang disertakan harus diizinkan konfigurasi.
Peran dan kelas selalu berasal dari akun server. Error berupa
`{"error":{"kode":"...","pesan":"..."}}` untuk galat yang ditangani; kegagalan tak
terduga dijawab `500 galat_server` dengan bentuk yang sama.

## Autentikasi

- POST `/auth/login/guru` atau `/auth/login/siswa`: `{identitas,kataSandi}` → `{pengguna}`.
- GET `/auth/saya` → `{pengguna}`. Data pengguna: `{id,nama,peran,wajibGantiSandi}`;
  siswa juga memiliki `{nis,kelas}` dengan kelas lengkap seperti `VIII A`.
- POST `/auth/ganti-sandi`: `{kataSandiLama,kataSandiBaru}` → 204. Lima kegagalan
  dalam 15 menit dijawab `429 terlalu_banyak`.
- POST `/auth/logout` → 204, sesi dicabut.

Login yang salah selalu 401 `login_gagal`. Hitungan gagal naik secara atomik; setelah
`MAKS_GAGAL_LOGIN` akun terkunci `KUNCI_MENIT` menit dan hitungannya kembali ke nol
saat masa kunci berakhir.

## State untuk frontend

GET `/state` → `{materi,soal,hasil,chat,aktivitas,dihapus}`.
Hanya pengguna aktif yang sudah mengganti sandi awal. Guru menerima seluruh kelas;
siswa menerima materi/soal kelasnya serta hasil/chat/aktivitas miliknya sendiri.
Nilai `dihapus` sementara 0, bukan metrik pembersihan fisik database.

Untuk kompatibilitas frontend saat ini, ID objek bisnis diserialisasi sebagai string
angka dan `waktu` sebagai Unix milliseconds. Nama `materi.kelas` berisi tingkat
(`VII`, `VIII`, `IX`), sedangkan kelas siswa/soal/hasil selalu kode lengkap.

## Materi

GET `/materi`, GET `/materi/{id}`: guru dan siswa. Objek di luar kelas siswa menjawab 404.

POST `/materi`, PUT `/materi/{id}`: guru; body
`{mapel,kelas,rombel,judul,teks,rangkuman?}`. `teks` dan `rangkuman` berupa array string;
`rombel` array minimal satu A–F. Mengembalikan objek dengan `id` string.

DELETE `/materi/{id}`: guru → 204. Soal terkait ikut dihapus.
POST `/materi/unggah` masih 501 (ekstraksi PDF/DOCX belum ada). Gunakan input teks.

## Soal

GET `/soal`: guru/siswa. Siswa tidak menerima `jawaban` atau `pembahasan`.
POST `/soal`, PUT `/soal/{id}`: guru; body
`{materiId,topik?,tanya,opsi,jawaban,kelas,pembahasan?,otomatis?}`.
Jawaban adalah indeks mulai 0 dan harus berada dalam batas opsi.
Kelas tujuan harus merupakan subset kelas materi sumber.
DELETE `/soal/{id}`: guru → 204.

POST `/soal/generate`: guru; `{materiId,jumlah?}` → `{usulan,jumlah,judul}`. Draft dibuat
di server dari kalimat berpola "X adalah Y" pada materi dan belum disimpan. Materi dengan
kurang dari tiga kalimat definisi dijawab `400 definisi_kurang`.

POST `/soal/terbitkan`: guru; `{usulan:[objekSoal,...]}` → `{jumlah,soal}` dan menyimpan
draft, termasuk penanda `otomatis`.

## Latihan

POST `/latihan/mulai`: siswa; `{materiId,ulangDari?}` → `{sesiId,soal,materiId,judul,mapel}`.
Daftar soal dibekukan server dan tidak membawa kunci. Soal yang ditambahkan guru setelah
titik ini tidak menggagalkan percobaan yang sedang berjalan.

POST `/latihan`: siswa;
`{materiId,jawaban:[{soalId,pilihan}],sesiId?,kunci?,ulangDari?}`.
`sesiId` mengunci daftar soal sesuai snapshot; sesi yang sudah dipakai menjawab
`409 sesi_dipakai`. `kunci` (teks unik dari klien) membuat pengumpulan idempoten: kiriman
kembar mengembalikan hasil yang sama, bukan baris baru. Tanpa `sesiId`, server memakai
seluruh soal yang tersedia (perilaku lama, tetap didukung).

Pilihan -1 berarti belum dijawab. Daftar harus memuat tepat seluruh soal yang tersedia
untuk materi itu; pada retry hanya soal salah dari hasil asal milik siswa tersebut.
Duplikat, soal dari kelas lain dan opsi di luar batas ditolak. Field nilai kiriman client
bukan sumber penilaian.

Respons hasil: `{id,materiId,waktu,kelas,nilai,benar,total,detail,ulangDari}`.
Detail memuat `{soalId,jawab,benar,kunci,pembahasan}` setelah submit. Kunci tidak
dikirim pada daftar soal sebelum submit.

## Chat dan rangkuman

POST `/chat`: siswa; `{pertanyaan}` → `{jawaban,alasan,sumber}`.
Jawaban dari pencarian materi kelas siswa, bukan LLM. Jika tidak cocok, jawaban null.
Pertanyaan dan jawaban disimpan di server.
POST `/rangkuman`: siswa; `{materiId}` → 204. Menyimpan aktivitas rangkuman milik siswa.

## Analisis, rekap, dan unduhan

GET `/analisis?tingkat=VIII&rombel=A`: guru → `{hasil,jumlahLatihan,rataRata}` (24 jam terakhir).
GET `/dashboard`: guru → `{materi,soal,latihan,rataRata}`.
Frontend menggunakan `/state` untuk merender rincian analisis.

DELETE `/analisis?tingkat=VIII&rombel=A`: guru. Tanpa `tingkat` dijawab
`400 lingkup_kurang`; menghapus hasil/aktivitas/chat/rekap hanya untuk kelas itu.
Mengembalikan `{dihapus:{hasil,aktivitas,chat,ringkasan_harian},lingkup}`.

GET `/rekap?tingkat=&rombel=&hari=30`: guru → `{baris,perKelas,totalLatihan,hari}`.
Isinya rekap harian yang tetap ada setelah data 24 jam dibersihkan `jalankan_retensi()`.

GET `/ekspor?tingkat=&rombel=`: guru → CSV UTF-8 berisi waktu, NIS, nama, kelas, materi,
benar, total, nilai. Tanpa parameter, seluruh kelas.

## Kelola akun siswa

Semua endpoint di bawah hanya untuk guru.

- GET `/kelas` → `{kelas:[{tingkat,rombel,kelas,siswa}],total}`; 18 kelas VII–IX A–F,
  termasuk kelas yang masih kosong.
- GET `/siswa?tingkat=&rombel=&cari=` → daftar
  `{id,nis,nama,tingkat,rombel,kelas,aktif,wajibGantiSandi}`.
- POST `/siswa`: `{nis,nama,tingkat,rombel}` → 201 `{siswa,kataSandiAwal}`; NIS ganda 409.
- POST `/siswa/impor`: `{baris:[{nis,nama,tingkat,rombel}]}` → `{dibuat,gagal,jumlah}`.
  Baris gagal dilaporkan satu per satu dan tidak membatalkan baris lain.
- PATCH `/siswa/{id}/status`: `{aktif:true|false}` → siswa. Menonaktifkan akun
  mencabut sesi yang sedang berjalan tanpa menghapus riwayat.
- POST `/siswa/{id}/reset-sandi` → `{kataSandiAwal,siswa}`. Sesi siswa itu dicabut dan
  akun kembali wajib ganti sandi.

Kata sandi awal hanya muncul pada respons pembuatan/reset; server menyimpan hash saja.
Lupa sandi guru diselesaikan lewat CLI: `python -m app.cli reset-sandi --email ...`.

## Kesehatan

GET `/health`: publik → `{status:"ok"}`, memeriksa koneksi database.
