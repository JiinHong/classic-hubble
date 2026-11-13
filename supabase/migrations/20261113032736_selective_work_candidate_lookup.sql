-- Keep canonical ranking in the application; narrow only the candidate reads.
create function public.search_work_candidates_v2(search_term text)
returns setof public.works language plpgsql stable security invoker set search_path = ''
set plan_cache_mode = force_custom_plan as $function$
declare
  k text := public.work_search_key(search_term);
  pat text;
begin
  if length(search_term) not between 1 and 200 or k = '' then return; end if;
  pat := '%' || replace(replace(replace(k, chr(92), chr(92)||chr(92)), '%', chr(92)||'%'), '_', chr(92)||'_') || '%';
  return query
    with composer_ids as (
      select c.id from public.composers c where c.search_text like pat
      union
      select c.id from public.composers c
      where length(k)>2 and k ~ '^[가-힣]+$' and c.search_text like ('%' || left(k,2) || '%')
      and exists (select 1 from regexp_split_to_table(public.work_search_normalize(coalesce(c.name_ko,c.name)), ' ') t
        where t ~ '^[가-힣]{2,}$' and length(k)>length(t) and starts_with(k,t))
    ), matches as (
      select w.id from public.works w where w.search_text like pat
      union select a.work_id from public.work_aliases a where a.search_text like pat
      union select w.id from public.works w join composer_ids c on c.id=w.composer_id
    )
    select w.* from public.works w join matches m on m.id=w.id;
end $function$;
revoke all on function public.search_work_candidates_v2(text) from public;
grant execute on function public.search_work_candidates_v2(text) to anon, authenticated, service_role;
