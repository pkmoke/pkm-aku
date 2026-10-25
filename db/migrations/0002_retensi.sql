-- Retensi 24 jam: rekap dulu ke ringkasan_harian, baru hapus. Satu pernyataan = atomik.
create or replace function jalankan_retensi()
returns table (hasil_dihapus int, aktivitas_dihapus int, chat_dihapus int, sesi_dihapus int)
language plpgsql as $$
declare
  n_hasil int; n_akt int; n_chat int; n_sesi int;
begin
  with lama as (
    delete from hasil where waktu < now() - interval '24 hours'
    returning kelas, nilai, waktu
  ), agg as (
    select (waktu at time zone 'Asia/Jakarta')::date as tanggal, kelas,
           count(*)::int as n, sum(nilai)::int as total
    from lama group by 1, 2
  ), rekap as (
    insert into ringkasan_harian (tanggal, kelas, jumlah_latihan, total_nilai)
    select tanggal, kelas, n, total from agg
    on conflict (tanggal, kelas) do update
      set jumlah_latihan = ringkasan_harian.jumlah_latihan + excluded.jumlah_latihan,
          total_nilai    = ringkasan_harian.total_nilai    + excluded.total_nilai
    returning 1
  )
  select count(*) into n_hasil from lama;

  delete from aktivitas where waktu < now() - interval '24 hours';
  get diagnostics n_akt = row_count;
  delete from chat where waktu < now() - interval '24 hours';
  get diagnostics n_chat = row_count;
  delete from sesi where kedaluwarsa < now();
  get diagnostics n_sesi = row_count;

  return query select n_hasil, n_akt, n_chat, n_sesi;
end $$;
