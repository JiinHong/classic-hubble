-- Keep the original available for long inputs, parity checks and rollback.
create function public.suggest_works_v2(search_term text)
returns table(slug text, title text, composer text)
language plpgsql stable security invoker set search_path = ''
set plan_cache_mode = force_custom_plan as $function$
declare
  k text := public.work_search_key(search_term);
  prefix text;
begin
  if search_term is null or length(search_term) not between 1 and 200 or k = '' then return; end if;
  if length(k) >= 3 then
    return query select s.slug, s.title, s.composer from public.suggest_works(search_term) s;
    return;
  end if;
  prefix := replace(replace(replace(k, chr(92), chr(92)||chr(92)), '%', chr(92)||'%'), '_', chr(92)||'_') || '%';
  return query
    with hits(work_id, priority) as (
      select a.work_id, case when a.search_text = k then 0 else 1 end
      from public.work_aliases a where a.search_text like prefix
      union all
      select w.id, case when public.work_search_key(w.title_ko) = k then 0 else 1 end
      from public.works w where public.work_search_key(w.title_ko) like prefix
      union all
      select w.id, case when public.work_search_key(w.title) = k then 0 else 1 end
      from public.works w where public.work_search_key(w.title) like prefix
      union all
      select w.id, 2 from public.works w join public.composers c on c.id = w.composer_id
      where exists (select 1 from regexp_split_to_table(public.work_search_normalize(c.name || ' ' || coalesce(c.name_ko,'')), ' ') t where t like prefix)
    ), best as (select h.work_id, min(h.priority) as priority from hits h group by h.work_id)
    select w.slug, coalesce(nullif(w.title_ko,''), w.title), coalesce(c.name_ko,c.name)
    from best b join public.works w on w.id = b.work_id join public.composers c on c.id = w.composer_id
    order by case when b.priority = 0 or public.work_search_key(w.catalogue) = k then 0 else b.priority end,
      w.popularity_rank nulls last, w.id
    limit 8;
end $function$;
revoke all on function public.suggest_works_v2(text) from public;
grant execute on function public.suggest_works_v2(text) to anon, authenticated, service_role;
