set local lock_timeout='3s';

-- A literal name normally identifies only one (or a few) composers.
alter function public.concert_named_composers(text) rows 4;
create index concert_venue_name_trgm on public.venues using gin (lower(name) extensions.gin_trgm_ops);
create index concert_venue_city_trgm on public.venues using gin (lower(city) extensions.gin_trgm_ops);

create or replace function public.concert_search_page(search_term text, city_name text, matched_work_ids uuid[], period_filter text, page_offset integer)
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
  ), matched_works as materialized (
    select w.id,w.slug from unnest(matched_work_ids) k
      cross join lateral (select id,slug from public.works where id=k offset 0) w
    union select w.id,w.slug from public.concert_named_composers(search_term) c
      cross join lateral (select id,slug from public.works where composer_id=c offset 0) w
  ), linked as materialized (
    select distinct on (pi.performance_id) pi.performance_id as id, w.slug
    from matched_works w cross join lateral (
      select performance_id,position,id from public.program_items where work_id=w.id offset 0
    ) pi
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
    union select k.id from literal_candidates k join public.performances p on p.id=k.id
      left join public.venues v on v.id=p.venue_id cross join input i
      where strpos(lower(p.title || ' ' || coalesce(v.name,'') || ' ' || coalesce(v.city,'')) ||
          case when cardinality(p.artists)>0 then ' '||public.concert_artist_text(p.artists) else '' end ||
          coalesce((select ' '||string_agg(public.concert_program_text(pi.composer_name,pi.display_title,pi.source_provider,pi.source_type),
            ' ' order by pi.position,pi.id) from public.program_items pi where pi.performance_id=p.id),''),i.q)>0
  ), candidates as (
    -- The indexed probe is intentionally not flattened into a catalog-wide hash join.
    select p.id,p.starts_at,p.ends_on,p.status,p.kopis_performance_id,p.venue_id,l.slug
    from input i join hit_ids h on i.q is distinct from ''
    cross join lateral (
      select id,starts_at,ends_on,status,kopis_performance_id,venue_id
      from public.performances where id=h.id offset 0
    ) p left join linked l on l.id=h.id
    union all
    -- Only an explicitly blank browse needs every concert. NULL means a selected work.
    select p.id,p.starts_at,p.ends_on,p.status,p.kopis_performance_id,p.venue_id,l.slug
    from input i join public.performances p on i.q='' left join linked l on l.id=p.id
  ), hits as materialized (
    select p.id,p.starts_at,coalesce(p.ends_on,(p.starts_at at time zone 'Asia/Seoul')::date) as last_day,
      coalesce(p.ends_on,(p.starts_at at time zone 'Asia/Seoul')::date)<i.today as past,
      (p.starts_at at time zone 'Asia/Seoul')::date<i.today as ongoing, p.slug, coalesce(v.city,'') as city
    from candidates p left join public.venues v on v.id=p.venue_id cross join input i
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
