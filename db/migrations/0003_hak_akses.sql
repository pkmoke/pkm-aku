-- Hak akses: hanya role bemai_app (backend) yang boleh menyentuh data.
-- RLS diaktifkan di SEMUA tabel. Tidak ada policy untuk anon/authenticated (API bawaan
-- Supabase), jadi kalau anon key bocor pun tidak ada baris yang bisa dibaca.

do $$
declare t text;
begin
  for t in select tablename from pg_tables where schemaname = 'public' loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

do $$
declare t text;
begin
  if exists (select from pg_roles where rolname = 'bemai_app') then
    for t in select tablename from pg_tables where schemaname = 'public' loop
      execute format('drop policy if exists backend_penuh on public.%I', t);
      execute format('create policy backend_penuh on public.%I for all to bemai_app using (true) with check (true)', t);
    end loop;
    grant usage on schema public to bemai_app;
    grant select, insert, update, delete on all tables in schema public to bemai_app;
    grant usage, select on all sequences in schema public to bemai_app;
    grant execute on function jalankan_retensi() to bemai_app;
    -- log_audit: backend hanya boleh menambah dan membaca, tidak mengubah/menghapus
    revoke update, delete on log_audit from bemai_app;
  else
    raise notice 'Role bemai_app belum ada; jalankan db/role-app.sql lalu ulangi migrasi ini.';
  end if;

  -- Cabut akses jalur API bawaan Supabase (role ini hanya ada di Supabase)
  if exists (select from pg_roles where rolname = 'anon') then
    revoke all on all tables in schema public from anon;
    revoke execute on function jalankan_retensi() from anon;
  end if;
  if exists (select from pg_roles where rolname = 'authenticated') then
    revoke all on all tables in schema public from authenticated;
    revoke execute on function jalankan_retensi() from authenticated;
  end if;
end $$;
