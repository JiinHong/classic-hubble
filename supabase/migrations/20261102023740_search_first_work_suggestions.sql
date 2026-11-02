set local lock_timeout = '3s';

create index work_aliases_suggest_prefix on public.work_aliases (search_text text_pattern_ops);
create index works_suggest_ko_prefix on public.works (public.work_search_key(title_ko) text_pattern_ops);
create index works_suggest_title_prefix on public.works (public.work_search_key(title) text_pattern_ops);

-- This is a small navigation list, not a replacement for authoritative work ranking.
create function public.suggest_works(search_term text)
returns table(slug text, title text, composer text)
language sql stable security invoker set search_path = '' as $function$
  with input as materialized (
    select public.work_search_normalize(search_term) as normalized,
      public.work_search_key(search_term) as key
    where length(search_term) between 1 and 200
      and public.work_search_key(search_term) <> ''
  ), needle as materialized (
    select i.*, replace(replace(replace(i.key, E'\\', E'\\\\'), '%', E'\\%'), '_', E'\\_') || '%' as prefix,
      (select token from regexp_split_to_table(i.normalized, ' ') token
       order by (token !~ '^\d+(번)?$') desc, length(token) desc, token limit 1) as anchor
    from input i
  ), short_composers as (
    select c.id from public.composers c, needle n
    where length(n.key) < 3 and exists (
      select 1 from regexp_split_to_table(public.work_search_normalize(c.name || ' ' || coalesce(c.name_ko, '')), ' ') token
      where token like n.prefix
    )
  ), ids as (
    select w.id from needle n cross join lateral public.search_work_candidates(n.anchor) w where length(n.key) >= 3
    union
    select a.work_id from public.work_aliases a, needle n where length(n.key) < 3 and a.search_text like n.prefix
    union
    select w.id from public.works w, needle n where length(n.key) < 3 and
      (public.work_search_key(w.title_ko) like n.prefix or public.work_search_key(w.title) like n.prefix)
    union
    select w.id from public.works w join short_composers c on c.id = w.composer_id
  ), candidates as (
    select w.*, coalesce(c.name_ko, c.name) as composer_label, c.search_text as composer_key,
      coalesce(a.keys, array[]::text[]) as aliases,
      coalesce(a.normalized, '') as alias_text
    from ids join public.works w on w.id = ids.id
    join public.composers c on c.id = w.composer_id
    left join lateral (
      select array_agg(wa.search_text) as keys,
        string_agg(public.work_search_normalize(wa.alias), ' ') as normalized
      from public.work_aliases wa where wa.work_id = w.id
    ) a on true
  ), ranked as (
    select w.*, case
      when n.key = any(w.aliases) or n.key in (public.work_search_key(w.title_ko), public.work_search_key(w.title), public.work_search_key(w.catalogue)) then 0
      when exists (select 1 from unnest(w.aliases || array[public.work_search_key(w.title_ko), public.work_search_key(w.title)]) v where v like n.prefix) then 1
      else 2 end as priority
    from candidates w, needle n
    where length(n.key) < 3 or not exists (
      select 1 from regexp_split_to_table(n.normalized, ' ') token
      where case
        when token ~ '^\d+(번)?$' then
          (' ' || public.work_search_normalize(w.title || ' ' || coalesce(w.title_ko, '') || ' ' || coalesce(w.catalogue, '')) || ' ' || w.alias_text || ' ')
            !~ ('(^|[^0-9])' || token || '([^0-9]|$)')
        else position(token in (w.search_text || w.composer_key || array_to_string(w.aliases, ' '))) = 0
      end
    )
  )
  select w.slug, coalesce(nullif(w.title_ko, ''), w.title), w.composer_label
  from ranked w order by w.priority, w.popularity_rank nulls last, w.id limit 8;
$function$;
revoke all on function public.suggest_works(text) from public;
grant execute on function public.suggest_works(text) to anon, authenticated, service_role;
