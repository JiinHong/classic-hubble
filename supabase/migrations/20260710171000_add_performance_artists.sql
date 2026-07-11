alter table public.performances
  add column artists text[] not null default '{}';
