-- Khusus Supabase (pg_cron tersedia). Aktifkan dulu: Dashboard -> Database -> Extensions -> pg_cron.
-- Lalu jalankan file ini sekali sebagai admin.
select cron.schedule('bemai-retensi', '0 * * * *', $$select * from jalankan_retensi()$$);
-- Cek: select * from cron.job;
-- Di Postgres lokal tanpa pg_cron, panggil manual: select * from jalankan_retensi();
