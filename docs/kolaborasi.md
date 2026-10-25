# Kolaborasi

Clone repository GitHub yang dibagikan pemilik proyek. Buat branch untuk perubahan,
lalu buka pull request agar perubahan dapat diperiksa sebelum digabungkan ke main.

```sh
git switch -c fitur/nama-perubahan
# edit dan uji perubahan
git add nama-file
git commit -m "Jelaskan perubahan"
git push -u origin fitur/nama-perubahan
```

Untuk mengambil perubahan terbaru setelah branch main diperbarui:

```sh
git switch main
git pull --ff-only
```

Salin `backend/.env.example` menjadi `backend/.env`, lalu isi konfigurasi untuk
lingkungan sendiri. Jangan commit password, token ngrok/GitHub, database, atau
kredensial akun uji. Akun uji pada laptop pemilik tidak ikut repository.

Lihat README untuk menjalankan aplikasi dan pengujian. Gunakan data fiktif;
beberapa temuan keamanan pada laporan audit masih perlu diperbaiki sebelum produksi.
