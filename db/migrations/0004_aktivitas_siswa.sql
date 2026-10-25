-- Riwayat aktivitas harus dipisahkan per akun, bukan hanya per kelas.
alter table aktivitas add column siswa_id uuid references pengguna on delete cascade;
create index aktivitas_siswa_idx on aktivitas(siswa_id,waktu);
