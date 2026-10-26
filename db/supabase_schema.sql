-- Optional: PostgreSQL schema for Supabase.
-- Run this in the Supabase SQL editor, then set SUPABASE_URL and SUPABASE_KEY in Streamlit secrets.
-- Without these secrets the app uses the bundled SQLite database instead.

create table if not exists public.trips (
    id            text primary key,
    title         text not null,
    destination   text not null,
    country       text,
    start_date    text,
    days          integer not null check (days between 1 and 30),
    budget_level  text,
    party         text,
    travellers    integer,
    total_inr     numeric,
    provider      text,
    payload       jsonb not null,
    created_at    text not null,
    updated_at    text not null
);

-- Normalised activity rows (useful for analytics / reporting dashboards).
create table if not exists public.trip_activities (
    id          bigint generated always as identity primary key,
    trip_id     text not null references public.trips(id) on delete cascade,
    day         integer not null,
    slot        text not null,
    start_time  text,
    place_name  text not null,
    category    text,
    lat         double precision,
    lon         double precision,
    cost_local  numeric
);

create index if not exists idx_trips_updated on public.trips (updated_at desc);
create index if not exists idx_activities_trip on public.trip_activities (trip_id);

-- Demo-friendly row-level security: anyone holding the anon key can manage trips.
-- Tighten these policies (e.g. per authenticated user) before real-world use.
alter table public.trips enable row level security;
create policy "demo read"   on public.trips for select using (true);
create policy "demo insert" on public.trips for insert with check (true);
create policy "demo update" on public.trips for update using (true);
create policy "demo delete" on public.trips for delete using (true);
