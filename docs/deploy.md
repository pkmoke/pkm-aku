# Deploy

Database di Supabase (cloud). Di server hanya dua container kecil: `api` dan `web`.
Jangan self-host Supabase di server yang sudah berisi aplikasi lain; terlalu berat.

## 1. Supabase

1. Buat project. Catat password database admin.
2. Jalankan dari laptop (butuh `psql`), memakai alamat **pooler** dari Dashboard -> Connect:
   ```
   export ADMIN_URL='postgresql://postgres.PROJECT_REF:PASSWORD_ADMIN@aws-0-REGION.pooler.supabase.com:5432/postgres'
   psql "$ADMIN_URL" -v sandi='SANDI-KUAT-UNTUK-BACKEND' -f db/role-app.sql
   for f in db/migrations/*.sql; do psql "$ADMIN_URL" -v ON_ERROR_STOP=1 -f "$f"; done
   psql "$ADMIN_URL" -f db/seed.sql
   ```
3. Dashboard -> Database -> Extensions: aktifkan `pg_cron`, lalu `psql "$ADMIN_URL" -f db/pg_cron.sql`.
   Cek berjalan: `select * from cron.job;`
4. Backend tidak memakai REST API bawaan Supabase. Tabel sudah dikunci RLS tanpa policy untuk `anon`/`authenticated`,
   jadi aman; kalau mau, nonaktifkan juga API itu di pengaturan project (nama menu bisa berbeda per versi dashboard).

## 2. Server

```
git clone <repo> && cd aplikasi-pkm
cp backend/.env.example backend/.env      # isi DATABASE_URL (user: bemai_app.PROJECT_REF), ASAL_DIIZINKAN
docker compose up -d --build
docker compose exec api python -m app.cli buat-guru --email guru@sekolah.sch.id --nama "Nama Guru"
```

Container `web` hanya mendengarkan `127.0.0.1:8081`. Cek dulu port bebas: `sudo ss -tlnp`.

## 3. Buka ke internet (HTTPS wajib)

Tambahkan satu server block di reverse proxy yang sudah ada (jangan sentuh yang lama):

```
server {
  server_name bemai.contoh.sch.id;
  # ... sertifikat Let's Encrypt ...
  location / {
    proxy_pass http://127.0.0.1:8081;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
  }
}
```

Isi `ASAL_DIIZINKAN` dengan `https://bemai.contoh.sch.id` dan `COOKIE_SECURE=true`.
