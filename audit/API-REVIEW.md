# Hasil pengujian API — 25 Oktober 2026

## Cakupan dan metode

1. Request nyata ke URL ngrok aktif: `GET https://husked-reappoint-from.ngrok-free.dev/api/health` menghasilkan HTTP 404, Content-Type text/html, Server SimpleHTTP/0.6 Python/3.14.7. Tunnel hanya mengarah frontend statis. Respons ini bukan penolakan autentikasi dari FastAPI dan tidak membuktikan API backend aman atau rentan.
2. Pengujian lokal menggunakan HTTP/ASGI FastAPI TestClient pada router aplikasi asli. Virtualenv terisolasi berada di /private/tmp/bemai-api-audit-venv; source aplikasi dan konfigurasi tunnel tidak diubah.
3. PostgreSQL tidak tersedia. Dependency koneksi diganti penyimpanan uji (fake), dan identitas guru/siswa diinjeksi untuk matriks RBAC. Tidak mengklaim pengujian login/sesi/SQL/RLS end-to-end, concurrency, nginx rate limit atau backend publik.

Jalankan ulang dari folder proyek:

```sh
/private/tmp/bemai-api-audit-venv/bin/python audit/api_checks.py
```

## Hasil

91 pemeriksaan cocok dengan perilaku yang dicatat, termasuk pemeriksaan yang sengaja mengonfirmasi kelemahan. Angka 91/91 **bukan** skor keamanan dan bukan berarti tidak ada vulnerability. Detail ada di api-results.json.

| Area | Hasil |
|---|---|
| 22 endpoint bisnis, tanpa cookie login | 401 |
| Cookie sesi tidak dikenal (lookup DB fake tidak menemukan sesi) | 401 |
| Identitas siswa ke 17 endpoint guru | 403 |
| Identitas guru ke 2 endpoint siswa | 403 |
| Identitas yang berwenang ke 22 endpoint bisnis | 501; fitur belum diimplementasi |
| Akun wajib ganti sandi, akses materi | 403 |
| Akun wajib ganti sandi, baca profil | 200 |
| Login tanpa header kustom, Origin asing atau Origin null | 403 |
| Cross-origin preflight | 405; tidak ada izin CORS |
| Body login kosong, field kosong, identitas/sandi terlalu panjang | 400 |
| Identitas tidak ada dan payload `' OR 1=1 --` | 401; identitas diteruskan sebagai parameter SQL ke fake driver |
| Swagger/OpenAPI default | 404 |
| Endpoint tidak dikenal | JSON error 404 |
| Respons normal endpoint profil | Cache-Control: no-store |

## Temuan yang berhasil dikonfirmasi melalui request lokal

### API-01 — Sedang: ganti-sandi tidak membatasi percobaan sandi lama yang salah

Endpoint: POST /api/auth/ganti-sandi.

Dengan identitas guru uji yang valid, kirim enam request berurutan:

```json
{"kataSandiLama":"incorrect","kataSandiBaru":"audit-new-password"}
```

Header: X-Requested-With: bemai; Origin: https://testserver.

Hasil: keenamnya HTTP 400 dengan jalur verifikasi Argon2 nyata. Tidak ada 429, counter kegagalan, atau INSERT audit kegagalan dalam seluruh panggilan DB yang dicatat. Tidak ada percobaan menebak sandi nyata; hanya enam input salah yang sama. Perubahan sandi tidak terjadi.

Lokasi: backend/app/routers/auth.py:100–113. Nginx hanya memasang limit_req pada /api/auth/login/; route ganti-sandi melewati location /api/ tanpa limit itu.

Dampak: pemilik sesi valid, termasuk sesi curian, dapat mengulang verifikasi sandi lama dan mengonsumsi resource hash. Tidak membuktikan sandi berhasil ditebak atau layanan dapat dijatuhkan. Pembatasan tambahan pada reverse proxy eksternal tidak diketahui dan tidak diuji.

Perbaikan: throttle per akun/sesi dan sumber, catat kegagalan, tambahkan kebijakan reautentikasi yang sesuai. Audit jangan merekam sandi. OWASP A07/A09; CWE-307.

### API-02 — Rendah: exception tak terduga tidak mengikuti kontrak JSON

Endpoint uji: GET /api/health. Dependency database uji sengaja melempar RuntimeError dengan marker unik.

Hasil: HTTP 500, Content-Type text/plain; charset=utf-8, body Internal Server Error. Marker internal tidak bocor. Handler JSON aplikasi hanya menangani Galat, HTTPException dan RequestValidationError; exception umum tidak mempunyai handler JSON.

Dampak: client menerima format berbeda dari docs/api.md sehingga pesan/kode error hilang. Tidak ada bukti stack trace atau credential bocor. Hasil ini bukan SQL exploit; fault injection dipakai untuk memeriksa penanganan kegagalan.

Perbaikan: handler exception umum yang mengembalikan JSON generik, logging server dengan correlation ID dan tanpa detail sensitif di respons.

## Yang belum bisa dinyatakan terbukti

- SQL injection: payload diteruskan sebagai parameter; tidak ada PostgreSQL nyata untuk mengevaluasi query. Tidak menemukan bukti bypass.
- Login sukses, password lockout dan reset setelah kedaluwarsa, pencabutan sesi, cookie dari login sukses, dan race condition: perlu PostgreSQL asli dan akun disposable.
- IDOR/akses objek lintas kelas, manipulasi nilai lewat API, upload traversal/RCE, prompt injection atau SSRF: endpoint bisnis masih 501. Tidak ada implementasi aktif untuk diuji.
- Rate limit nginx, TLS, proxy-header trust dan keamanan database/Supabase: tidak diuji melalui TestClient.

Prioritas berikutnya untuk pengujian end-to-end: jalankan PostgreSQL test terpisah, aplikasikan migrasi dan role aplikasi, buat akun disposable, jalankan backend/tests/test_auth_dan_rbac.py, lalu tambah pengujian concurrency login serta object authorization setelah endpoint bisnis diimplementasi.
