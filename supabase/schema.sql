create extension if not exists pgcrypto;

create type performance_status as enum ('open', 'upcoming', 'soldout', 'closed');
create type program_source_type as enum ('official', 'verified', 'ocr', 'estimated', 'unknown');
create type program_publication_status as enum (
  'unknown',
  'confirmed',
  'image_only',
  'not_published',
  'selected_on_day',
  'announced_later'
);
create type review_state as enum ('needs_review', 'approved', 'rejected');
create type notification_channel as enum ('email', 'web_push');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.venues (
  id uuid primary key default gen_random_uuid(),
  kopis_facility_id text unique,
  name text not null,
  city text not null,
  booking_channels text[] not null default '{}',
  address text,
  phone text,
  homepage_url text,
  latitude double precision,
  longitude double precision,
  seat_count integer check (seat_count is null or seat_count >= 0),
  hall_count integer check (hall_count is null or hall_count >= 0),
  characteristic text,
  opening_year integer,
  amenities jsonb not null default '{}'
    check (jsonb_typeof(amenities) = 'object'),
  accessibility jsonb not null default '{}'
    check (jsonb_typeof(accessibility) = 'object'),
  raw_payload jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.composers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  name_ko text,
  period text,
  created_at timestamptz not null default now()
);

create table public.works (
  id uuid primary key default gen_random_uuid(),
  composer_id uuid not null references public.composers(id) on delete restrict,
  slug text not null unique,
  title text not null,
  title_ko text,
  catalogue text,
  instrumentation text,
  popularity_rank integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.work_aliases (
  id uuid primary key default gen_random_uuid(),
  work_id uuid not null references public.works(id) on delete cascade,
  alias text not null,
  locale text not null default 'ko',
  source text not null default 'curated',
  unique (work_id, alias)
);

create table public.venue_halls (
  id uuid primary key default gen_random_uuid(),
  venue_id uuid not null references public.venues(id) on delete cascade,
  kopis_hall_id text not null unique,
  name text not null,
  seat_count integer check (seat_count is null or seat_count >= 0),
  disabled_seat_count integer
    check (disabled_seat_count is null or disabled_seat_count >= 0),
  stage_metadata jsonb not null default '{}'
    check (jsonb_typeof(stage_metadata) = 'object'),
  raw_payload jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.performances (
  id uuid primary key default gen_random_uuid(),
  kopis_performance_id text unique,
  venue_id uuid references public.venues(id) on delete set null,
  venue_hall_id uuid references public.venue_halls(id) on delete set null,
  title text not null,
  starts_at timestamptz not null,
  starts_on date,
  ends_on date,
  status performance_status not null default 'upcoming',
  artists text[] not null default '{}',
  price_range text,
  booking_url text,
  booking_links jsonb not null default '[]'
    check (jsonb_typeof(booking_links) = 'array'),
  poster_url text,
  intro_image_urls text[] not null default '{}',
  source_label text,
  schedule_text text,
  runtime_text text,
  age_text text,
  synopsis text,
  program_status program_publication_status not null default 'unknown',
  program_source_url text,
  program_image_urls text[] not null default '{}',
  program_source_updated_at timestamptz,
  provider_updated_at timestamptz,
  raw_payload jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (starts_on is null or ends_on is null or ends_on >= starts_on)
);

create table public.program_items (
  id uuid primary key default gen_random_uuid(),
  performance_id uuid not null references public.performances(id) on delete cascade,
  work_id uuid references public.works(id) on delete set null,
  display_title text not null,
  composer_name text,
  source_type program_source_type not null default 'unknown',
  confidence numeric(4, 3) not null default 0,
  position integer not null default 0,
  source_provider text not null default 'unknown'
    check (btrim(source_provider) <> ''),
  source_url text,
  created_at timestamptz not null default now()
);

create table public.poster_review_items (
  id uuid primary key default gen_random_uuid(),
  performance_id uuid not null references public.performances(id) on delete cascade,
  image_url text not null,
  extracted_text text,
  suggested_work_id uuid references public.works(id) on delete set null,
  confidence numeric(4, 3) not null default 0,
  state review_state not null default 'needs_review',
  reviewer_id uuid references public.profiles(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.watchlist_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  work_id uuid not null references public.works(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_id, work_id)
);

create table public.notification_preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  channel notification_channel not null,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, channel)
);

create table public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  user_agent text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.notification_deliveries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  performance_id uuid references public.performances(id) on delete cascade,
  work_id uuid references public.works(id) on delete cascade,
  channel notification_channel not null,
  delivered_at timestamptz,
  error text,
  created_at timestamptz not null default now()
);

create table public.ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running',
  counters jsonb not null default '{}',
  error text
);

create table public.provider_records (
  id uuid primary key default gen_random_uuid(),
  provider text not null check (btrim(provider) <> ''),
  entity_type text not null check (btrim(entity_type) <> ''),
  provider_id text not null check (btrim(provider_id) <> ''),
  ingestion_run_id uuid references public.ingestion_runs(id) on delete set null,
  payload jsonb not null,
  fetched_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (provider, entity_type, provider_id)
);

create index performances_starts_at_idx on public.performances (starts_at);
create index performances_venue_id_idx on public.performances (venue_id);
create index performances_venue_hall_id_idx on public.performances (venue_hall_id);
create index venue_halls_venue_id_idx on public.venue_halls (venue_id);
create index program_items_work_id_idx on public.program_items (work_id);
create index program_items_performance_id_idx on public.program_items (performance_id);
create unique index program_items_performance_provider_position_uidx
  on public.program_items (performance_id, source_provider, position);
create index work_aliases_alias_idx on public.work_aliases using gin (to_tsvector('simple', alias));
create index poster_review_state_idx on public.poster_review_items (state, created_at);
create index poster_review_performance_id_idx on public.poster_review_items (performance_id);
create index poster_review_suggested_work_id_idx on public.poster_review_items (suggested_work_id);
create index poster_review_reviewer_id_idx on public.poster_review_items (reviewer_id);
create unique index poster_review_performance_image_uidx
  on public.poster_review_items (performance_id, image_url);
create index watchlist_user_idx on public.watchlist_items (user_id);
create index watchlist_work_id_idx on public.watchlist_items (work_id);
create index works_composer_id_idx on public.works (composer_id);
create index push_subscriptions_user_id_idx on public.push_subscriptions (user_id);
create index notification_deliveries_user_id_idx on public.notification_deliveries (user_id);
create index notification_deliveries_performance_id_idx on public.notification_deliveries (performance_id);
create index notification_deliveries_work_id_idx on public.notification_deliveries (work_id);
create index provider_records_ingestion_run_id_idx
  on public.provider_records (ingestion_run_id);
create index provider_records_fetched_at_idx
  on public.provider_records (fetched_at desc);

alter table public.profiles enable row level security;
alter table public.venues enable row level security;
alter table public.composers enable row level security;
alter table public.works enable row level security;
alter table public.work_aliases enable row level security;
alter table public.venue_halls enable row level security;
alter table public.performances enable row level security;
alter table public.program_items enable row level security;
alter table public.poster_review_items enable row level security;
alter table public.watchlist_items enable row level security;
alter table public.notification_preferences enable row level security;
alter table public.push_subscriptions enable row level security;
alter table public.notification_deliveries enable row level security;
alter table public.ingestion_runs enable row level security;
alter table public.provider_records enable row level security;

create policy "venues are publicly readable"
  on public.venues for select
  using (true);

create policy "composers are publicly readable"
  on public.composers for select
  using (true);

create policy "works are publicly readable"
  on public.works for select
  using (true);

create policy "work aliases are publicly readable"
  on public.work_aliases for select
  using (true);

create policy "venue halls are publicly readable"
  on public.venue_halls for select
  to anon, authenticated
  using (true);

create policy "performances are publicly readable"
  on public.performances for select
  using (true);

create policy "program items are publicly readable"
  on public.program_items for select
  using (true);

create policy "poster review items are service-role managed"
  on public.poster_review_items for all
  using (false)
  with check (false);

create policy "ingestion runs are service-role managed"
  on public.ingestion_runs for all
  using (false)
  with check (false);

create policy "provider records are service-role managed"
  on public.provider_records for all
  to service_role
  using (true)
  with check (true);

create policy "profiles are self-readable"
  on public.profiles for select
  using ((select auth.uid()) = id);

create policy "profiles are self-insertable"
  on public.profiles for insert
  with check ((select auth.uid()) = id);

create policy "profiles are self-updatable"
  on public.profiles for update
  using ((select auth.uid()) = id);

create policy "watchlist owner access"
  on public.watchlist_items for all
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "notification preference owner access"
  on public.notification_preferences for all
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "push subscription owner access"
  on public.push_subscriptions for all
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "delivery owner read"
  on public.notification_deliveries for select
  using ((select auth.uid()) = user_id);

revoke all on table public.provider_records from anon, authenticated;
grant all on table public.provider_records to service_role;
grant select on table public.venue_halls to anon, authenticated;
grant all on table public.venue_halls to service_role;
