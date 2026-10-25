# Audit logika dan keamanan Bemai

Tanggal: 25 Oktober 2026. Lingkup: seluruh source aplikasi dalam bemai-chatbot-main: modul Python/FastAPI, ES modules frontend, HTML, SQL/migrasi/seed, Docker/nginx, konfigurasi dependency, dokumentasi dan pengujian. File gambar bukan executable source. Tidak ada perubahan pada source aplikasi; audit menambahkan laporan dan pemeriksaan reproduksi.

## Kesimpulan

Belum layak digunakan untuk data atau penilaian nyata. Frontend secara eksplisit masih prototipe lokal: autentikasi, penyimpanan dan penilaian tidak memakai API. Backend sudah mempunyai fondasi autentikasi, tetapi seluruh endpoint bisnis masih 501. Konsekuensi prototipe dibedakan dari kerentanan backend; tidak ada bukti bahwa seseorang dapat menembus RBAC backend hanya dengan mengganti peran frontend.

Ada 13 temuan utama di bawah. Severity menilai dampak bila dipakai untuk operasional sekolah; untuk demo dengan data fiktif, dampaknya lebih rendah. Penamaan kategori mengikuti OWASP Top 10:2025; CWE melengkapi masalah di luar kategori tersebut. Tidak semua kategori OWASP harus menghasilkan temuan.

## Temuan keamanan dan integritas

### S01 — Tinggi: login frontend tidak memverifikasi identitas dan peran

Lokasi: frontend/src/js/main.js:20–43; frontend/src/js/api.js:1; frontend/index.html:70–73.

Bukti statis: pilihRole menerima student/teacher dari tombol. masuk hanya mengubah tampilan dan kelas; loginUser/loginPass tidak diperiksa dan loginGuru/loginSiswa tidak dipanggil. Pilih Guru lalu Masuk dengan sandi apa pun akan membuka pengelolaan data lokal. keluar juga hanya mengubah tampilan, bukan memanggil logout API.

Dampak: siapa pun pada browser itu dapat mengubah/menghapus materi, soal dan analisis lokal. Ini perilaku demo yang sudah didokumentasikan, tetapi deployment produksi memakai frontend yang sama. Bukan bypass endpoint backend.

Perbaikan: sambungkan login, /auth/saya, ganti sandi awal dan logout; gunakan peran/kelas dari server. Implementasikan endpoint bisnis dan simpan perubahan melalui API. Backend tetap menjadi otoritas setiap operasi.

Pemetaan: A01 Broken Access Control, A07 Authentication Failures; CWE-602.

### S02 — Tinggi: kunci jawaban dan nilai sepenuhnya dikendalikan browser

Lokasi: frontend/src/js/status.js:12–25; frontend/src/js/siswa/latihan.js:94–107; frontend/src/js/data-contoh.js; backend/app/routers/latihan.py.

Bukti statis: seluruh db.soal beserta jawaban disimpan/dimuat di localStorage bemai.v1; kumpulkanLatihan membandingkan pilihan dengan s.jawaban dan menyimpan hasil lokal. Kunci dapat dibaca sebelum mengerjakan dan hasil dapat diedit melalui DevTools. Tidak perlu membobol sesi server. Materi/hasil antarperangkat juga tidak sinkron.

Perbaikan: kirim hanya pertanyaan/opsi sebelum submit, nilai di server berdasarkan siswa dan daftar soal yang berwenang; server menyimpan hasil dan baru mengirim pembahasan setelah submit. Jangan mempercayai nilai/identitas kiriman browser.

Pemetaan: A08 Software or Data Integrity Failures, A06 Insecure Design; CWE-602.

### S03 — Sedang: data pengguna bercampur dan percakapan bertahan setelah logout

Lokasi: frontend/src/js/siswa/riwayat.js:6–11; frontend/src/js/konstanta.js:1–2; frontend/src/js/siswa/latihan.js:103; frontend/src/js/main.js:37–43; frontend/src/js/ui.js:77–93.

Bukti statis: satu storage key untuk semua pengguna, nama siswa konstan Andi, riwayat difilter hanya kelas, bukan siswa_id. Logout tidak membersihkan #messages atau hasil rangkuman; pergantian kelas/peran mempertahankan percakapan sebelumnya di DOM. Pada perangkat bersama, pengguna berikut dapat melihat aktivitas/percakapan sebelumnya. Ini bukan kebocoran lintas akun database yang sudah dibuktikan; frontend belum memiliki akun asli.

Perbaikan: asosiasikan hasil/chat/aktivitas dengan ID akun di server; filter ownership di server. Kosongkan seluruh state sensitif dan batalkan callback tertunda saat logout/pergantian pengguna.

Pemetaan: A01; CWE-200, CWE-613.

### S04 — Sedang: counter gagal login mengalami lost update pada request paralel

Lokasi: backend/app/routers/auth.py:38–55.

Bukti statis: SELECT membaca gagal_login, Python menghitung +1, kemudian UPDATE menetapkan angka absolut tanpa row lock. Dua request dapat membaca angka 0 lalu keduanya menulis 1; jumlah percobaan sebelum akun terkunci menjadi lebih banyak daripada konfigurasi. Ada nginx limit per IP sehingga ini bukan klaim brute force tanpa batas. Belum diuji dengan PostgreSQL paralel.

Perbaikan: buat increment/penentuan lock atomik di SQL atau serialisasikan state autentikasi per akun dengan transaksi/row lock. Uji request gagal paralel dan interaksi login sukses/gagal.

Pemetaan: A07; CWE-362, CWE-307.

### S05 — Sedang: percobaan sandi lama di ganti-sandi tidak dibatasi atau diaudit ketika gagal

Lokasi: backend/app/routers/auth.py:100–113; frontend/nginx.conf:15–39.

Bukti statis: endpoint memverifikasi Argon2 pada setiap request; sandi lama salah langsung menghasilkan 400 tanpa counter/audit kegagalan. Nginx limit hanya di /api/auth/login/. Penyerang harus memiliki sesi valid terlebih dahulu. Ia dapat mencoba sandi lama berulang kali dan mengonsumsi CPU/memori; sesi yang dicuri dapat dipakai untuk mencoba mengambil alih kredensial permanen. Tidak ada load test dan tidak diklaim telah menjatuhkan layanan.

Perbaikan: rate limit per akun/sesi/IP pada verifikasi kredensial sensitif, audit kegagalan tanpa menyimpan sandi, dan reautentikasi/rotasi sesi untuk perubahan kredensial.

Pemetaan: A07, A09; CWE-307, CWE-400.

### S06 — Sedang: counter gagal login tidak direset setelah masa kunci berakhir

Lokasi: backend/app/routers/auth.py:39–55.

Bukti statis: setelah lima kegagalan counter tetap 5. Setelah terkunci_sampai lewat, satu sandi salah menghasilkan 6 dan langsung mengunci 15 menit lagi. Hanya login sukses yang menghapus counter. Pelaku yang mengetahui NIS/email dapat mempertahankan penguncian korban dengan satu permintaan setiap masa kunci berakhir. Penguncian berbasis akun juga memungkinkan denial of service awal dengan lima request; perlu menyeimbangkan proteksi dan pemulihan.

Perbaikan: tetapkan semantik jendela kegagalan secara eksplisit, reset/decay counter yang sudah kedaluwarsa secara atomik, serta tambahkan throttling per sumber dan pemulihan akun.

Pemetaan: A07, A06; CWE-645.

## Kesalahan logika dan keandalan

### L01 — Sedang: tombol filter analisis tidak terhubung ke handler

Lokasi: frontend/src/js/guru/analisis.js:14–16; frontend/src/js/main.js:78–79 dan dispatcher click.

Reproduksi terarah berhasil: markup memakai data-act="status.filterTingkat" dan "status.filterRombel", tetapi AKSI hanya mempunyai filterTingkat dan filterRombel. Klik diabaikan; rincian per rombel tidak dapat dicapai lewat tombol normal.

Perbaikan: samakan nama data-act dan handler, lalu uji klik tingkat dan rombel sungguhan.

### L02 — Sedang: rincian materi mengabaikan filter kelas ketika menghitung nilai

Lokasi: frontend/src/js/guru/analisis.js:77–84.

Reproduksi terarah berhasil: materi yang sama, VIII A nilai 100 dan VIII B nilai 0; ketika filter VIII A aktif, distribusi benar menunjukkan 100, tetapi rincian materi menunjukkan 2 latihan dengan rata-rata 50. Query rincian menggunakan status.db.hasil penuh.

Perbaikan: gunakan hasilFilter() untuk agregasi materi, dengan semantik filter yang sama seperti bagian lain.

### L03 — Sedang: publikasi soal lintas kelas menghasilkan soal yang tidak bisa dipilih

Lokasi: frontend/src/js/guru/soal.js:89–104; frontend/src/js/siswa/latihan.js:14–15; frontend/src/js/seleksi.js:13.

Reproduksi seleksi berhasil: materi VIII A dengan soal yang diterbitkan ke VII B menghasilkan 1 soal VII B, tetapi 0 materi yang tersedia. Pemilih latihan mengharuskan materiSiswa() sehingga soal tersebut tidak muncul, walaupun guru diberi opsi terbit lintas tingkat/rombel. Edit tujuan materi juga dapat menimbulkan keadaan ini.

Perbaikan: putuskan aturan konsisten: batasi kelas soal ke kelas materi, atau sediakan materi/akses latihan lintas kelas secara eksplisit. Jangan hanya memperluas filter materi tanpa mempertimbangkan batas akses.

### L04 — Rendah: chatbot mengembalikan sukses tanpa isi jawaban

Lokasi: frontend/src/js/siswa/chat.js:26–33, 82–86.

Reproduksi terarah berhasil: judul "Fotosintesis", isi "Daun mengubah cahaya menjadi energi.", pertanyaan "Fotosintesis". Bonus kecocokan judul menghasilkan ok=true tetapi jawab=[]; pengguna memperoleh bubble/sumber tanpa jawaban.

Perbaikan: sukses memerlukan kandidat kalimat, atau gunakan fallback isi materi yang relevan dan terdefinisi.

### L05 — Sedang: kegagalan localStorage dianggap berhasil menyimpan

Lokasi: frontend/src/js/status.js:24–25; frontend/src/js/guru/editor.js:33; frontend/src/js/guru/materi.js:49–53.

Reproduksi terarah berhasil: setItem yang melempar QuotaExceededError ditelan simpanKe(). UI tetap memberi toast tersimpan dan bisa mengosongkan formulir; setelah reload perubahan hilang. Upload/teks tanpa batas memperbesar kemungkinan quota habis. muat() juga menangkap error migrasi dan mengganti data dengan seed sehingga storage rusak dapat tertimpa tanpa peringatan.

Perbaikan: laporkan kegagalan penyimpanan; jangan memberi sukses/mengosongkan input sebelum penyimpanan berhasil; validasi skema dan cadangkan data gagal migrasi sebelum recovery.

Pemetaan tambahan: A10 Mishandling of Exceptional Conditions; CWE-390.

### L06 — Rendah: retensi 24 jam tidak konsisten saat aplikasi lama terbuka

Lokasi: frontend/src/js/status.js:49–70; frontend/src/js/guru/analisis.js:10; frontend/src/js/guru/dashboard.js:5; frontend/src/js/siswa/riwayat.js:6.

Bukti statis: pembersihan hanya saat modul dimuat dan renderAnalisis. Dashboard/riwayat tidak membersihkan atau memfilter waktu. Tab terbuka lebih dari sehari dapat terus menampilkan hasil kedaluwarsa, walaupun UI menyatakan hanya satu hari terakhir. Di SQL, cron setiap jam berarti penghapusan fisik juga bukan tepat pada detik ke-24 jam; ini karakteristik jadwal, bukan bypass.

Perbaikan: filter query berdasarkan cutoff saat membaca; jadwal retensi terpisah untuk pembersihan fisik, dan jelaskan toleransinya.

## Dependency/build: risiko teridentifikasi, bukan CVE runtime terkonfirmasi

### D01 — Rendah: dependency dan image tidak dikunci

Lokasi: backend/requirements.txt:1–6; backend/Dockerfile:1–5; frontend/Dockerfile:2; frontend/package.json:7.

Rentang versi luas, tidak ada lockfile/hashes, image nginx:alpine dan python:3.12-slim bergerak; npx --yes serve mengambil executable eksternal ketika script dev dijalankan. Versi artefak terpasang/deploy tidak tersedia sehingga audit ini tidak dapat menetapkan CVE mana yang benar-benar aktif.

Contoh batas yang perlu diperbaiki: python-multipart>=0.0.9 masih mengizinkan versi lama yang memiliki advisory. Advisory GHSA-59g5-xgcq-4qw3 menjelaskan DoS parser; GHSA-wp53-j4wj-2cfg menjelaskan arbitrary file write pada konfigurasi nondefault. Tidak ada parser upload aktif pada route stub sekarang, dan konfigurasi prasyarat arbitrary file write tidak ditemukan. Jangan melaporkan kedua CVE sebagai exploit yang terbukti pada aplikasi ini.

Perbaikan: kunci versi hasil resolusi yang sudah diaudit, hashes dan image digest, jalankan SCA terhadap artefak/image nyata pada CI, dan hindari unduhan executable dev tanpa versi tetap.

Pemetaan: A03 Software Supply Chain Failures.

## Cakupan OWASP Top 10:2025

| Kategori | Hasil |
|---|---|
| A01 Broken Access Control | S01, S03 pada frontend prototipe. RBAC server ada; object-level authorization endpoint bisnis belum dapat diuji karena 501. |
| A02 Security Misconfiguration | Tidak ada exploit terkonfirmasi. Secure cookie default aktif, docs default mati, port web/DB dev terikat localhost. Wildcard trust proxy perlu dievaluasi bila akses container berubah. |
| A03 Software Supply Chain Failures | D01; versi deploy/CVE aktual belum diketahui. |
| A04 Cryptographic Failures | Tidak ada kelemahan kriptografi yang terkonfirmasi: Argon2 untuk sandi, token acak 32 byte dan SHA-256 untuk token di DB. Verifikasi sertifikat DB belum dievaluasi pada deployment nyata. |
| A05 Injection | SQL yang diperiksa memakai parameter; interpolasi kondisi login berasal dari konstanta server. Rendering teks utama menggunakan text nodes/escaping. Tidak ditemukan jalur SQLi/XSS remote yang terbukti. Ada innerHTML dengan ID/data lokal yang tidak selalu di-escape; jangan menganggapnya XSS remote tanpa sumber input yang bisa dikendalikan penyerang. |
| A06 Insecure Design | S02, S06. |
| A07 Authentication Failures | S01, S04, S05, S06. |
| A08 Software or Data Integrity Failures | S02. |
| A09 Security Logging and Alerting Failures | Kegagalan ganti-sandi tidak dicatat (S05). Audit login tersedia; monitoring/alert eksternal belum diketahui. |
| A10 Mishandling of Exceptional Conditions | L05. Error tak tertangani DB juga belum mempunyai handler JSON 500 sesuai kontrak API; bukan bukti stack trace bocor ke klien. |

SSRF, command injection, path traversal, unsafe deserialization, upload execution, dan prompt injection LLM: tidak ada jalur aktif yang terbukti. Upload backend dan integrasi LLM masih stub; komentar instruksi keamanan bukan implementasi. Skema SQL memisahkan kunci soal dan memakai RLS; ini tidak menggantikan authorization bisnis saat endpoint nanti diisi.

## Verifikasi dan batas audit

- `node audit/checks.cjs`: lima reproduksi terarah berhasil. Harness menjalankan source JS asli di VM dengan dependency/DOM/storage tiruan; bukan pengujian browser end-to-end.
- Seluruh 21 file Python berhasil diparse dengan ast.parse; ini hanya pemeriksaan sintaks.
- Tests asli Playwright dan pytest/Postgres tidak dijalankan: Playwright, pytest, Docker dan psql tidak tersedia pada lingkungan audit. Tidak ada database test yang dikonfigurasi.
- Tes RBAC yang ada membolehkan 501 sebagai tanda lolos penjaga. Kelulusan tes tersebut tidak membuktikan CRUD, pembatasan objek/kelas, grading, atau upload aman.
- Tidak melakukan load test, pemindaian deployment publik, perubahan data nyata, instalasi dependency, atau eksploitasi destruktif.
- Tidak ada lockfile, image build atau inventaris dependency runtime untuk SCA lengkap. Tidak ada bukti credential produksi dalam file yang tersedia; pemeriksaan riwayat Git tidak dilakukan karena folder source tidak memuat repositori .git.

Prioritas: sambungkan autentikasi/API dan penilaian server (S01–S03), implementasikan endpoint bisnis dengan object authorization, benahi state login atomik serta throttling (S04–S06), lalu perbaiki bug analisis/publikasi/persistensi dan bangun pengujian integrasi yang mencakup alur nyata.

## Sumber eksternal

- OWASP Top 10:2025: https://top10.owasp.org/2025/
- Advisory upstream multipart DoS: https://github.com/Kludex/python-multipart/security/advisories/GHSA-59g5-xgcq-4qw3
- Advisory upstream multipart file write dengan konfigurasi nondefault: https://github.com/Kludex/python-multipart/security/advisories/GHSA-wp53-j4wj-2cfg
