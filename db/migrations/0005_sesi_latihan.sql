-- Sesi latihan bertanda tangan server, idempotensi pengumpulan, dan penanda soal otomatis.

alter table soal add column if not exists otomatis boolean not null default false;

alter table hasil add column if not exists kunci text;
create unique index if not exists hasil_kunci_uq on hasil (siswa_id, kunci) where kunci is not null;

create table if not exists latihan_sesi (
  id         uuid primary key default gen_random_uuid(),
  siswa_id   uuid not null references pengguna on delete cascade,
  materi_id  bigint references materi on delete set null,
  soal_ids   bigint[] not null,
  ulang_dari bigint references hasil on delete set null,
  dibuat     timestamptz not null default now(),
  dipakai    timestamptz
);
create index if not exists latihan_sesi_siswa_idx on latihan_sesi (siswa_id, dibuat);

-- Tabel baru di luar jangkauan 0003: hak akses role backend harus ditambahkan di sini.
alter table latihan_sesi enable row level security;
do $$
begin
  if exists (select from pg_roles where rolname = 'bemai_app') then
    drop policy if exists backend_penuh on latihan_sesi;
    create policy backend_penuh on latihan_sesi for all to bemai_app using (true) with check (true);
    grant select, insert, update, delete on latihan_sesi to bemai_app;
  end if;
end $$;
