set local lock_timeout = '3s';

-- Restrict the shortcut to an actual name or whole name token. Other work
-- titles/aliases (including tributes by other composers) still use the TS ranker.
create function public.concert_named_composers(term text) returns setof uuid
language sql stable security invoker set search_path = '' as $$
  with n as (select lower(normalize(btrim(term), NFC)) as q)
  select c.id from public.composers c, n
  where char_length(n.q) between 1 and 200 and n.q ~ '^[[:alpha:]]+( [[:alpha:]]+)*$'
    and c.search_text like '%' || replace(n.q, ' ', '') || '%'
    and (n.q in (lower(c.name), lower(c.name_ko)) or
      n.q = any(string_to_array(lower(c.name || ' ' || coalesce(c.name_ko,'')), ' ')))
$$;

create function public.concert_rank_work_candidates(search_term text, literal_name text)
returns setof public.works language sql stable security invoker set search_path = '' as $$
  select w.* from public.search_work_candidates(search_term) w
  where w.composer_id not in (select public.concert_named_composers(literal_name))
$$;

create function public.concert_artist_text(names text[]) returns text
language sql immutable parallel safe set search_path = '' as $$
  select lower(coalesce(array_to_string(names, ' '), ''))
$$;
create index concerts_title_literal_trgm on public.performances using gin (lower(title) extensions.gin_trgm_ops);
create index concerts_artist_literal_trgm on public.performances using gin (public.concert_artist_text(artists) extensions.gin_trgm_ops);

create function public.concert_program_text(composer text,title text,provider text,kind public.program_source_type)
returns text language sql immutable parallel safe set search_path = '' as $$
  select lower(coalesce(composer,'') || ' ' || title || ' ' || case provider
    when 'nol' then 'NOL 원문' when 'codex_vision' then '이미지 판독' when 'paddleocr' then 'OCR 근거 확인'
    else case kind when 'estimated' then '추정 매칭' when 'official' then '공식 확인'
      when 'ocr' then 'OCR 추출' when 'verified' then '검수 완료' else '확인 필요' end end)
$$;

create index concert_program_literal_trgm on public.program_items using gin
  (public.concert_program_text(composer_name,display_title,source_provider,source_type) extensions.gin_trgm_ops);

create function public.concert_search_page(search_term text, city_name text, matched_work_ids uuid[], period_filter text, page_offset integer)
returns table(upcoming_count bigint, past_count bigint, performance_ids uuid[], match_slugs text[], available_cities text[])
language sql stable security invoker set search_path = '' as $$
  with input as materialized (
    select lower(btrim(search_term)) q, (now() at time zone 'Asia/Seoul')::date today
    where coalesce(length(search_term),0) <= 200 and length(city_name)<=80
      and page_offset between 0 and 1000000 and period_filter in ('all','past','upcoming')
  ), needle as materialized (
    select '%' || replace(replace(replace(t,E'\\',E'\\\\'), '%', E'\\%'), '_', E'\\_') || '%' pat
    from input i cross join lateral regexp_split_to_table(i.q,'\s+') t
    where t<>'' order by length(t) desc limit 1
  ), work_ids as (
    select unnest(matched_work_ids) as id
    union select w.id from public.works w where w.composer_id in (select public.concert_named_composers(search_term))
  ), linked as materialized (
    select distinct on (pi.performance_id) pi.performance_id as id, w.slug
    from work_ids m join public.program_items pi on pi.work_id=m.id join public.works w on w.id=m.id
    order by pi.performance_id,pi.position,pi.id
  ), literal_candidates as (
    select p.id from public.performances p,needle n where lower(p.title) like n.pat
    union select p.id from public.performances p,needle n where public.concert_artist_text(p.artists) like n.pat
    union select p.id from public.venues v join public.performances p on p.venue_id=v.id,needle n
      where lower(v.name) like n.pat or lower(v.city) like n.pat
    union select pi.performance_id from public.program_items pi,needle n
      where public.concert_program_text(pi.composer_name,pi.display_title,pi.source_provider,pi.source_type) like n.pat
  ), hit_ids as (
    select id from linked
    union select p.id from public.performances p,input i where i.q=''
    union select k.id from literal_candidates k join public.performances p on p.id=k.id
      left join public.venues v on v.id=p.venue_id cross join input i
      where strpos(lower(p.title || ' ' || coalesce(v.name,'') || ' ' || coalesce(v.city,'')) ||
          case when cardinality(p.artists)>0 then ' '||public.concert_artist_text(p.artists) else '' end ||
          coalesce((select ' '||string_agg(public.concert_program_text(pi.composer_name,pi.display_title,pi.source_provider,pi.source_type),
            ' ' order by pi.position,pi.id) from public.program_items pi where pi.performance_id=p.id),''),i.q)>0
  ), hits as materialized (
    select p.id,p.starts_at,coalesce(p.ends_on,(p.starts_at at time zone 'Asia/Seoul')::date) as last_day,
      coalesce(p.ends_on,(p.starts_at at time zone 'Asia/Seoul')::date)<i.today as past,
      (p.starts_at at time zone 'Asia/Seoul')::date<i.today as ongoing, l.slug, coalesce(v.city,'') as city
    from hit_ids h join public.performances p on p.id=h.id left join public.venues v on v.id=p.venue_id
    left join linked l on l.id=p.id cross join input i
    where (p.kopis_performance_id is null or p.kopis_performance_id not like 'perf-%')
      and (p.status<>'closed' or coalesce(p.ends_on,(p.starts_at at time zone 'Asia/Seoul')::date)<i.today)
  ), region as materialized (
    select * from hits where city_name='전체' or city=city_name
  ), page as (
    select id,slug,row_number() over o as ord from region
    where period_filter='all' or past=(period_filter='past')
    window o as (order by past, case when not past then ongoing end,case when not past then starts_at end,
      case when past then last_day end desc,case when past then starts_at end desc,id)
    order by ord limit 24 offset greatest(0,least(page_offset,1000000))
  )
  select count(*) filter(where not past),count(*) filter(where past),
    array(select id from page order by ord),array(select slug from page order by ord),
    array(select distinct city from hits where city<>'' order by city) from region
$$;

revoke all on function public.concert_named_composers(text),public.concert_rank_work_candidates(text,text),
  public.concert_artist_text(text[]),public.concert_program_text(text,text,text,public.program_source_type),
  public.concert_search_page(text,text,uuid[],text,integer) from public;
grant execute on function public.concert_named_composers(text),public.concert_rank_work_candidates(text,text),
  public.concert_artist_text(text[]),public.concert_program_text(text,text,text,public.program_source_type),
  public.concert_search_page(text,text,uuid[],text,integer) to anon,authenticated,service_role;
