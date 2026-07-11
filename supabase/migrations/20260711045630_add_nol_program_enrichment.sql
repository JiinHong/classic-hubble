create type public.program_publication_status as enum (
  'unknown',
  'confirmed',
  'image_only',
  'not_published',
  'selected_on_day',
  'announced_later'
);

alter table public.performances
  add column program_status public.program_publication_status
    not null default 'unknown',
  add column program_source_url text,
  add column program_image_urls text[] not null default '{}',
  add column program_source_updated_at timestamptz;

alter table public.program_items
  add column source_provider text not null default 'unknown',
  add column source_url text,
  add constraint program_items_source_provider_check
    check (btrim(source_provider) <> '');

create unique index program_items_performance_provider_position_uidx
  on public.program_items (performance_id, source_provider, position);
