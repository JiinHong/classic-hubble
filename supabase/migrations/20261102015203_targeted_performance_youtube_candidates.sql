-- This is a deliberately lossy recall key, NOT the final matching normalizer.
-- Keep ASCII and decomposed Hangul; discard punctuation/marks/other scripts.
-- Empty keys are retained as candidates, so unsupported scripts cannot disappear.
create or replace function public.catalog_candidate_key(value text)
returns text language sql immutable parallel safe set search_path = '' as $$
  select regexp_replace(lower(normalize(coalesce(value, ''), NFD)),
    U&'[^a-z0-9\1100-\11ff]', '', 'g')
$$;

alter table public.works
  add column youtube_title_key text generated always as (public.catalog_candidate_key(title)) stored,
  add column youtube_title_ko_key text generated always as (public.catalog_candidate_key(title_ko)) stored;
alter table public.work_aliases
  add column youtube_alias_key text generated always as (public.catalog_candidate_key(alias)) stored;

create index performances_upcoming_end_idx on public.performances
  ((coalesce(ends_on, (starts_at at time zone 'Asia/Seoul')::date)))
  where status <> 'closed' and (kopis_performance_id is null or kopis_performance_id not like 'perf-%');

create or replace function public.youtube_work_candidates(video_text text)
returns setof public.works language sql stable security invoker set search_path = '' as $$
  with input as materialized (
    select public.catalog_candidate_key(video_text) as key
    where char_length(video_text) <= 20501
  ), mentioned_composers as materialized (
    -- Any name token is a conservative superset of the matcher's full/last names.
    -- Return all works by these composers to preserve full-name precedence,
    -- credits, rejection of conflicting composers, and catalogue-only matches.
    select c.id from public.composers c cross join input i
    where exists (
      select 1 from regexp_split_to_table(c.name || ' ' || coalesce(c.name_ko, ''), '[^[:alnum:]]+') token
      where token <> '' and strpos(i.key, public.catalog_candidate_key(token)) > 0
    )
  ), candidate_ids as (
    select w.id from public.works w where w.composer_id in (select id from mentioned_composers)
    union
    select w.id from public.works w cross join input i
    where strpos(i.key, w.youtube_title_key) > 0
       or (w.title_ko is not null and strpos(i.key, w.youtube_title_ko_key) > 0)
    union
    select a.work_id from public.work_aliases a cross join input i
    where strpos(i.key, a.youtube_alias_key) > 0
  )
  select w.* from public.works w join candidate_ids c on c.id = w.id
$$;

create or replace function public.search_performance_candidates(
  search_term text, city_name text, matched_work_ids uuid[]
) returns setof public.performances language sql stable security invoker set search_path = '' as $$
  with input as materialized (
    -- A whole literal match necessarily contains its longest whitespace token.
    -- Token retrieval also avoids depending on ordering among equal-position items.
    select public.catalog_candidate_key(coalesce((
      select token from regexp_split_to_table(search_term, '\s+') token
      order by char_length(token) desc limit 1
    ), '')) as key
    where char_length(search_term) <= 200 and char_length(city_name) <= 80
  )
  select p.* from public.performances p
  left join public.venues v on v.id = p.venue_id
  cross join input i
  where p.status <> 'closed'
    and coalesce(p.ends_on, (p.starts_at at time zone 'Asia/Seoul')::date)
      >= (current_timestamp at time zone 'Asia/Seoul')::date
    and (p.kopis_performance_id is null or p.kopis_performance_id not like 'perf-%')
    and (city_name = '전체' or coalesce(v.city, '') = city_name)
    and (
      i.key = ''
      or exists (select 1 from public.program_items pi where pi.performance_id = p.id and pi.work_id = any(matched_work_ids))
      or strpos(public.catalog_candidate_key(concat_ws(' ', p.title, v.name, v.city, array_to_string(p.artists, ' '))), i.key) > 0
      or exists (
        select 1 from public.program_items pi where pi.performance_id = p.id
        and strpos(public.catalog_candidate_key(concat_ws(' ', pi.composer_name, pi.display_title,
          case pi.source_provider
            when 'nol' then 'NOL 원문' when 'codex_vision' then '이미지 판독' when 'paddleocr' then 'OCR 근거 확인'
            else case pi.source_type when 'estimated' then '추정 매칭' when 'official' then '공식 확인'
              when 'ocr' then 'OCR 추출' when 'verified' then '검수 완료' else '확인 필요' end
          end)), i.key) > 0
      )
    )
$$;

create or replace function public.youtube_upcoming_links(work_ids uuid[])
returns table(work_id uuid, performance_id text)
language sql stable security invoker set search_path = '' as $$
  select links.work_id, links.performance_id from (
    select distinct pi.work_id, coalesce(p.kopis_performance_id, p.title) as performance_id,
      ((p.starts_at at time zone 'Asia/Seoul')::date < (current_timestamp at time zone 'Asia/Seoul')::date) as ongoing,
      date_trunc('minute', p.starts_at at time zone 'Asia/Seoul') as minute_at, p.starts_at, p.id
    from public.program_items pi join public.performances p on p.id = pi.performance_id
    where cardinality(work_ids) between 1 and 100 and pi.work_id = any(work_ids)
      and p.status <> 'closed'
      and coalesce(p.ends_on, (p.starts_at at time zone 'Asia/Seoul')::date) >= (current_timestamp at time zone 'Asia/Seoul')::date
      and (p.kopis_performance_id is null or p.kopis_performance_id not like 'perf-%')
  ) links order by links.work_id, links.ongoing, links.minute_at, links.starts_at, links.id
$$;

revoke all on function public.catalog_candidate_key(text) from public;
revoke all on function public.youtube_work_candidates(text) from public;
revoke all on function public.search_performance_candidates(text, text, uuid[]) from public;
revoke all on function public.youtube_upcoming_links(uuid[]) from public;
grant execute on function public.catalog_candidate_key(text), public.youtube_work_candidates(text),
  public.search_performance_candidates(text, text, uuid[]), public.youtube_upcoming_links(uuid[])
  to anon, authenticated, service_role;
