begin;
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null check (char_length(trim(name)) between 1 and 200),
  created_at timestamptz not null default now()
);
create index if not exists projects_owner_id_idx on public.projects(owner_id);
alter table public.projects enable row level security;
revoke all on table public.projects from public, anon;
grant select, insert, update, delete on table public.projects to authenticated;
drop policy if exists "Owners can read their projects" on public.projects;
create policy "Owners can read their projects" on public.projects for select to authenticated using (owner_id = (select auth.uid()));
drop policy if exists "Owners can create their projects" on public.projects;
create policy "Owners can create their projects" on public.projects for insert to authenticated with check (owner_id = (select auth.uid()));
drop policy if exists "Owners can update their projects" on public.projects;
create policy "Owners can update their projects" on public.projects for update to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
drop policy if exists "Owners can delete their projects" on public.projects;
create policy "Owners can delete their projects" on public.projects for delete to authenticated using (owner_id = (select auth.uid()));
notify pgrst, 'reload schema';
commit;
