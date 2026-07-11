alter table public.venues
  add column address text,
  add column phone text,
  add column homepage_url text,
  add column latitude double precision,
  add column longitude double precision,
  add column seat_count integer,
  add column hall_count integer,
  add column characteristic text,
  add column opening_year integer,
  add column amenities jsonb not null default '{}'::jsonb,
  add column accessibility jsonb not null default '{}'::jsonb,
  add column raw_payload jsonb not null default '{}'::jsonb,
  add column updated_at timestamptz not null default now(),
  add constraint venues_seat_count_check
    check (seat_count is null or seat_count >= 0),
  add constraint venues_hall_count_check
    check (hall_count is null or hall_count >= 0),
  add constraint venues_amenities_object_check
    check (jsonb_typeof(amenities) = 'object'),
  add constraint venues_accessibility_object_check
    check (jsonb_typeof(accessibility) = 'object');

create table public.venue_halls (
  id uuid primary key default gen_random_uuid(),
  venue_id uuid not null references public.venues(id) on delete cascade,
  kopis_hall_id text not null unique,
  name text not null,
  seat_count integer,
  disabled_seat_count integer,
  stage_metadata jsonb not null default '{}'::jsonb,
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint venue_halls_seat_count_check
    check (seat_count is null or seat_count >= 0),
  constraint venue_halls_disabled_seat_count_check
    check (disabled_seat_count is null or disabled_seat_count >= 0),
  constraint venue_halls_stage_metadata_object_check
    check (jsonb_typeof(stage_metadata) = 'object')
);

alter table public.performances
  add column venue_hall_id uuid references public.venue_halls(id) on delete set null,
  add column starts_on date,
  add column ends_on date,
  add column schedule_text text,
  add column runtime_text text,
  add column age_text text,
  add column synopsis text,
  add column booking_links jsonb not null default '[]'::jsonb,
  add column intro_image_urls text[] not null default '{}',
  add column provider_updated_at timestamptz,
  add constraint performances_date_range_check
    check (starts_on is null or ends_on is null or ends_on >= starts_on),
  add constraint performances_booking_links_array_check
    check (jsonb_typeof(booking_links) = 'array');

create table public.provider_records (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  entity_type text not null,
  provider_id text not null,
  ingestion_run_id uuid references public.ingestion_runs(id) on delete set null,
  payload jsonb not null,
  fetched_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (provider, entity_type, provider_id),
  constraint provider_records_provider_check
    check (btrim(provider) <> ''),
  constraint provider_records_entity_type_check
    check (btrim(entity_type) <> ''),
  constraint provider_records_provider_id_check
    check (btrim(provider_id) <> '')
);

create index venue_halls_venue_id_idx
  on public.venue_halls (venue_id);
create index performances_venue_hall_id_idx
  on public.performances (venue_hall_id);
create index provider_records_ingestion_run_id_idx
  on public.provider_records (ingestion_run_id);
create index provider_records_fetched_at_idx
  on public.provider_records (fetched_at desc);
create unique index poster_review_performance_image_uidx
  on public.poster_review_items (performance_id, image_url);

alter table public.venue_halls enable row level security;
alter table public.provider_records enable row level security;

create policy "venue halls are publicly readable"
  on public.venue_halls for select
  to anon, authenticated
  using (true);

revoke all on table public.provider_records from anon, authenticated;
grant all on table public.provider_records to service_role;
grant select on table public.venue_halls to anon, authenticated;
grant all on table public.venue_halls to service_role;
