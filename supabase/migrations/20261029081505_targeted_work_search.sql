-- Candidate retrieval only. The shared TypeScript matcher remains authoritative.
set local lock_timeout = '3s';
create extension if not exists pg_trgm with schema extensions;

create function public.work_search_normalize(value text)
returns text language plpgsql immutable parallel safe security invoker
set search_path = '' as $function$
declare
  result text := lower(normalize(coalesce(value, ''), NFC));
  genre text[];
begin
  foreach genre slice 1 in array array[
    array['피협', '피아노 협주곡'], array['바협', '바이올린 협주곡'],
    array['피소', '피아노 소나타'], array['현사', '현악 사중주']
  ] loop
    result := regexp_replace(result, '(' || genre[1] || ')\s*(?:제\s*)?(\d+)(?:번)?(?=$|\s|[^가-힣\d])', ' ' || genre[2] || ' \2번 ', 'g');
    result := regexp_replace(result, '(' || genre[1] || ')(?=\s|$)', ' ' || genre[2] || ' ', 'g');
  end loop;
  result := regexp_replace(result, '현악\s*4중주', '현악 사중주', 'g');
  result := regexp_replace(result, '(?:제\s*)?(\d+)\s*(?:번|곡)(?=$|\s|[^가-힣])', ' \1번 ', 'g');
  result := regexp_replace(result, $regex$[.,:;'"“”‘’〈〉<>()\[\]\-]$regex$, ' ', 'g');
  return btrim(regexp_replace(result, '\s+', ' ', 'g'));
end;
$function$;

create function public.work_search_key(value text)
returns text language sql immutable parallel safe security invoker
set search_path = '' as $function$
  select replace(public.work_search_normalize(value), ' ', '');
$function$;

-- Short (one/two-character) searches have no trigrams. Stored keys keep their
-- fallback scan cheap as well, without running normalization on every request.
alter table public.works add column search_text text generated always as (
  public.work_search_key(title || E'\n' || coalesce(title_ko, '') || E'\n' || coalesce(catalogue, ''))
) stored;
alter table public.work_aliases add column search_text text generated always as (public.work_search_key(alias)) stored;
alter table public.composers add column search_text text generated always as (
  public.work_search_key(name || E'\n' || coalesce(name_ko, ''))
) stored;
create index works_search_trgm on public.works using gin (search_text extensions.gin_trgm_ops);
create index work_aliases_search_trgm on public.work_aliases using gin (search_text extensions.gin_trgm_ops);
create index composers_search_trgm on public.composers using gin (search_text extensions.gin_trgm_ops);
create index works_search_order on public.works (popularity_rank asc nulls last, id);

create function public.search_work_candidates(search_term text)
returns setof public.works language sql stable security invoker
set search_path = '' as $function$
  with needle as materialized (
    select public.work_search_key(search_term) as term,
      '%' || replace(replace(replace(public.work_search_key(search_term), E'\\', E'\\\\'), '%', E'\\%'), '_', E'\\_') || '%' as pattern
    where length(search_term) between 1 and 200 and public.work_search_key(search_term) <> ''
  ), composer_ids as (
    select c.id from public.composers c, needle n
    where c.search_text like n.pattern
    union
    -- The matcher splits joined Korean composer names, e.g. 모차르트터키풍.
    select c.id from public.composers c, needle n,
      lateral regexp_split_to_table(public.work_search_normalize(coalesce(c.name_ko, c.name)), ' ') as names(token)
    where names.token ~ '^[가-힣]{2,}$' and n.term ~ '^[가-힣]+$'
      and length(n.term) > length(names.token) and starts_with(n.term, names.token)
  ), candidate_ids as (
    select w.id from public.works w, needle n
    where w.search_text like n.pattern
    union
    select a.work_id from public.work_aliases a, needle n where a.search_text like n.pattern
    union
    select w.id from public.works w join composer_ids c on c.id = w.composer_id
  )
  select w.* from public.works w join candidate_ids c on c.id = w.id;
$function$;

create function public.work_upcoming_links(work_ids uuid[])
returns table(work_id uuid, performance_id text) language sql stable security invoker
set search_path = '' as $function$
  select distinct pi.work_id, coalesce(p.kopis_performance_id, p.title)
  from public.program_items pi join public.performances p on p.id = pi.performance_id
  where pi.work_id = any(work_ids) and cardinality(work_ids) <= 24
    and p.status <> 'closed'
    and (p.kopis_performance_id is null or p.kopis_performance_id not like 'perf-%')
    and coalesce(p.ends_on, (p.starts_at at time zone 'Asia/Seoul')::date) >= (now() at time zone 'Asia/Seoul')::date;
$function$;

create function public.home_catalog_overview()
returns table(work_count bigint, upcoming_count bigint, confirmed_count bigint, performance_ids uuid[])
language sql stable security invoker set search_path = '' as $function$
  with upcoming as materialized (
    select p.id, p.starts_at,
      (p.starts_at at time zone 'Asia/Seoul')::date < (now() at time zone 'Asia/Seoul')::date as ongoing
    from public.performances p
    where p.status <> 'closed'
      and (p.kopis_performance_id is null or p.kopis_performance_id not like 'perf-%')
      and coalesce(p.ends_on, (p.starts_at at time zone 'Asia/Seoul')::date) >= (now() at time zone 'Asia/Seoul')::date
  )
  select (select count(*) from public.works), (select count(*) from upcoming),
    (select count(*) from upcoming u where exists(select 1 from public.program_items pi where pi.performance_id = u.id)),
    array(select id from upcoming order by ongoing, starts_at, id limit 4);
$function$;

revoke all on function public.work_search_normalize(text), public.work_search_key(text), public.search_work_candidates(text), public.work_upcoming_links(uuid[]), public.home_catalog_overview() from public;
grant execute on function public.work_search_normalize(text), public.work_search_key(text), public.search_work_candidates(text), public.work_upcoming_links(uuid[]), public.home_catalog_overview() to anon, authenticated, service_role;
