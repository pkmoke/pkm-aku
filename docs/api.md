# API terhubung

Prefix `/api`; cookie sesi HttpOnly. Request perubahan data memerlukan
`X-Requested-With: bemai`; Origin yang disertakan harus diizinkan konfigurasi.
Peran dan kelas selalu berasal dari akun server. Error berupa
`{"error":{"kode":"...","pesan":"..."}}` untuk galat yang ditangani.

## Autentikasi

- POST `/auth/login/guru` atau `/auth/login/siswa`: `{identitas,kataSandi}` → `{pengguna}`.
- GET `/auth/saya` → `{pengguna}`. Data pengguna: `{id,nama,peran,wajibGantiSandi}`;
  siswa juga memiliki `{nis,kelas}` dengan kelas lengkap seperti `VIII A`.
- POST `/auth/ganti-sandi`: `{kataSandiLama,kataSandiBaru}` → 204.
- POST `/auth/logout` → 204, sesi dicabut.

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
POST `/materi/unggah` masih 501. Gunakan input teks.

## Soal

GET `/soal`: guru/siswa. Siswa tidak menerima `jawaban` atau `pembahasan`.
POST `/soal`, PUT `/soal/{id}`: guru; body
`{materiId,topik?,tanya,opsi,jawaban,kelas,pembahasan?}`.
Jawaban adalah indeks mulai 0 dan harus berada dalam batas opsi.
Kelas tujuan harus merupakan subset kelas materi sumber.
DELETE `/soal/{id}`: guru → 204.
POST `/soal/terbitkan`: guru; `{usulan:[objekSoal,...]}` → `{jumlah,soal}`.
POST `/soal/generate` masih 501; draft dapat dibuat oleh generator definisi frontend.

## Latihan

POST `/latihan`: siswa;
`{materiId,jawaban:[{soalId,pilihan}],ulangDari?}`.
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

## Analisis dan dashboard

GET `/analisis?tingkat=VIII&rombel=A`: guru → `{hasil,jumlahLatihan,rataRata}`.
GET `/dashboard`: guru → `{materi,soal,latihan,rataRata}`.
Frontend menggunakan `/state` untuk merender rincian analisis.
DELETE `/analisis`: guru → 204, hapus hasil/aktivitas/chat/rekap; log audit tetap ada.
GET `/health`: publik → `{status:"ok"}`, memeriksa koneksi database.

Endpoint `/kelas`, `/siswa`, `/siswa/impor`, `/siswa/{id}/reset-sandi` masih 501.
