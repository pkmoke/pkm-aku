-- Skema Bemai. Nama kolom snake_case; backend yang memetakan ke camelCase di JSON (docs/api.md).

create table pengguna (
  id                uuid primary key default gen_random_uuid(),
  peran             text not null check (peran in ('guru', 'siswa')),
  nama              text not null,
  email             text,
  nis               text,
  tingkat           text check (tingkat in ('VII', 'VIII', 'IX')),
  rombel            text check (rombel in ('A', 'B', 'C', 'D', 'E', 'F')),
  kata_sandi_hash   text not null,
  aktif             boolean not null default true,
  wajib_ganti_sandi boolean not null default true,
  gagal_login       int not null default 0,
  terkunci_sampai   timestamptz,
  dibuat            timestamptz not null default now(),
  -- guru wajib email, siswa wajib NIS + kelas; kolom yang bukan miliknya harus kosong
  constraint pengguna_peran_lengkap check (
    (peran = 'guru'  and email is not null and nis is null and tingkat is null and rombel is null) or
    (peran = 'siswa' and nis is not null and tingkat is not null and rombel is not null and email is null)
  )
);
create unique index pengguna_email_uq on pengguna (lower(email));
create unique index pengguna_nis_uq on pengguna (nis);

-- Hanya hash token yang disimpan; peran SELALU dibaca dari tabel pengguna, bukan dari sini.
create table sesi (
  token_hash  text primary key,
  pengguna_id uuid not null references pengguna on delete cascade,
  dibuat      timestamptz not null default now(),
  kedaluwarsa timestamptz not null
);
create index sesi_pengguna_idx on sesi (pengguna_id);
create index sesi_kedaluwarsa_idx on sesi (kedaluwarsa);

create table materi (
  id        bigint generated always as identity primary key,
  mapel     text not null,
  tingkat   text not null check (tingkat in ('VII', 'VIII', 'IX')),
  -- selalu eksplisit (tidak ada "kosong = semua"); minimal satu rombel
  rombel    text[] not null default '{A,B,C,D,E,F}'
            check (cardinality(rombel) >= 1 and rombel <@ array['A','B','C','D','E','F']),
  judul     text not null,
  teks      text[] not null,
  rangkuman text[] not null default '{}'
);

create table soal (
  id         bigint generated always as identity primary key,
  materi_id  bigint references materi on delete cascade,
  topik      text,
  tanya      text not null,
  opsi       text[] not null check (cardinality(opsi) >= 2),
  pembahasan text,
  kelas      text[] not null check (cardinality(kelas) >= 1 and kelas <@ array[
    'VII A','VII B','VII C','VII D','VII E','VII F',
    'VIII A','VIII B','VIII C','VIII D','VIII E','VIII F',
    'IX A','IX B','IX C','IX D','IX E','IX F'])
);
create index soal_materi_idx on soal (materi_id);

-- Kunci jawaban dipisah supaya query soal untuk siswa tidak pernah membawanya.
create table soal_kunci (
  soal_id bigint primary key references soal on delete cascade,
  jawaban int not null check (jawaban >= 0)
);

create table hasil (
  id         bigint generated always as identity primary key,
  siswa_id   uuid references pengguna on delete set null,
  materi_id  bigint references materi on delete set null,
  kelas      text not null,
  nilai      int not null check (nilai between 0 and 100),
  benar      int not null,
  total      int not null,
  detail     jsonb not null default '[]',
  ulang_dari bigint references hasil on delete set null,
  waktu      timestamptz not null default now()
);
create index hasil_waktu_idx on hasil (waktu);
create index hasil_kelas_idx on hasil (kelas);

create table aktivitas (
  id    bigint generated always as identity primary key,
  waktu timestamptz not null default now(),
  tipe  text, judul text, hasil text, kelas text
);
create index aktivitas_waktu_idx on aktivitas (waktu);

create table chat (
  id         bigint generated always as identity primary key,
  siswa_id   uuid references pengguna on delete set null,
  kelas      text,
  pertanyaan text not null,
  jawaban    text,
  materi_id  bigint references materi on delete set null,
  waktu      timestamptz not null default now()
);
create index chat_waktu_idx on chat (waktu);

-- Rekap yang tetap ada setelah data 24 jam dibuang. Disimpan total_nilai (bukan rata-rata)
-- supaya penggabungan beberapa kali pembersihan di hari yang sama tetap tertimbang benar.
create table ringkasan_harian (
  tanggal        date not null,
  kelas          text not null,
  jumlah_latihan int  not null default 0,
  total_nilai    int  not null default 0,
  rata_rata      numeric generated always as (
    case when jumlah_latihan > 0 then round(total_nilai::numeric / jumlah_latihan, 1) end) stored,
  primary key (tanggal, kelas)
);

-- Tidak kena retensi 24 jam: fungsinya jejak keamanan, bukan data analisis.
create table log_audit (
  id          bigint generated always as identity primary key,
  waktu       timestamptz not null default now(),
  pengguna_id uuid,
  aksi        text not null,
  ip          inet,
  keterangan  text
);
create index log_audit_waktu_idx on log_audit (waktu);
