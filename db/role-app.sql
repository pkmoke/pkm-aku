-- Jalankan SEKALI, sebagai admin database, SEBELUM migrasi:
--   psql "$ADMIN_URL" -v sandi='ganti-dengan-sandi-kuat' -f db/role-app.sql
-- Role ini yang dipakai backend. Bukan superuser, tidak bisa membuat/mengubah tabel.
select format('create role bemai_app login password %L', :'sandi')
where not exists (select from pg_roles where rolname = 'bemai_app') \gexec
