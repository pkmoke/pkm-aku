# Clone, pull, push, dan kolaborasi GitHub

Repository proyek: [pkmoke/pkm-aku](https://github.com/pkmoke/pkm-aku).
Isi aplikasi `bemai-chatbot-main` ditempatkan langsung di root repository, sehingga
setelah clone terdapat `backend/`, `frontend/`, `db/`, dan `docker-compose.dev.yml`.
File `.env`, database lokal, token, cache dan kredensial uji tidak disertakan.

## 1. Mengambil seluruh kode pertama kali (clone)

Pasang Git, lalu buka Terminal atau PowerShell pada folder tujuan:

```sh
git clone https://github.com/pkmoke/pkm-aku.git
cd pkm-aku
```

Repository ini dapat di-clone tanpa akun jika tetap publik. Untuk mengirim perubahan,
Anda perlu login GitHub dan memiliki akses tulis, atau menggunakan fork.

Panduan menjalankan: [menjalankan.md](menjalankan.md).

## 2. Mengambil pembaruan (pull)

Jalankan dari folder repository yang sudah di-clone:

```sh
git status
git switch main
git pull --ff-only origin main
```

Commit atau simpan perubahan lokal Anda sebelum berpindah branch. Jika pull ditolak
karena riwayat bercabang, periksa `git log --oneline --graph --all`; jangan gunakan
force atau reset yang menghapus pekerjaan tanpa memahami perubahan lokal.

Pull mengambil pembaruan dari GitHub ke komputer. Push mengirim commit dari komputer
ke GitHub. Clone digunakan sekali saat mengambil repository untuk pertama kali.

## 3. Menyiapkan identitas commit dan login

Atur identitas untuk repository ini menggunakan identitas Anda sendiri:

```sh
git config user.name "Nama Anda"
git config user.email "email-anda@example.com"
```

GitHub CLI opsional dapat dipakai untuk login tanpa menempelkan password ke perintah:

```sh
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
```

Ikuti otorisasi di browser. Jangan menulis token/password dalam URL remote, file source,
commit, atau pesan chat. Jika menggunakan SSH, daftarkan public key melalui pengaturan
akun GitHub dan gunakan URL SSH repository.

## 4. Membuat perubahan dan push

```sh
git switch main
git pull --ff-only origin main
git switch -c fitur/nama-perubahan
# Edit dan uji kode sesuai panduan menjalankan.
git status
git add path/ke/file-yang-diubah
git diff --cached
git commit -m "Jelaskan perubahan secara singkat"
git push -u origin fitur/nama-perubahan
```

Buka repository di GitHub lalu pilih **Compare & pull request**. Minta rekan meninjau
perubahan sebelum digabungkan ke `main`. Tidak perlu mengirim kredensial akun pemilik.

## 5. Memberi akses tulis kepada teman

Pemilik repository dapat membuka **Settings → Collaborators** (nama menu dapat berbeda
pada repository organisasi), lalu mengundang username GitHub teman. Teman perlu menerima
undangan sebelum dapat push. Tanpa undangan, teman tetap dapat membaca repository publik
dan mengirim perubahan melalui fork/pull request.

Jangan membagikan akun atau password pemilik untuk kolaborasi. Dokumen ini tidak
mengirim undangan atau mengubah akses repository secara otomatis.

## 6. File yang tidak boleh ikut commit

- `backend/.env` dan variasi file `.env` lokal.
- Token GitHub/ngrok, private key, password database atau akun nyata.
- Database/volume lokal, `node_modules/`, `.venv/`, `__pycache__/`, log dan cache.
- `audit/CONNECTED.md` serta hasil JSON audit lokal yang dapat berisi detail sesi uji.

`backend/.env.example` sengaja disertakan sebagai contoh konfigurasi. Salin dan isi
sendiri; akun dan data pada laptop pemilik tidak otomatis ikut ketika Anda clone.
