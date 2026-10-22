-- NOL refreshes and repairs share one atomic, source-scoped write path.
create or replace function public.replace_nol_program_items(
  p_performance_id uuid,
  p_items jsonb,
  p_expected jsonb default null
) returns boolean
language plpgsql security invoker set search_path = ''
as $$
declare
  v_before jsonb;
  v_expected jsonb;
  v_actual jsonb;
  v_after jsonb;
begin
  if p_items is null or jsonb_typeof(p_items) <> 'array' then
    raise exception 'Program items must be an array';
  end if;
  if p_expected is not null and jsonb_typeof(p_expected) <> 'array' then
    raise exception 'Expected snapshot must be an array';
  end if;
  perform 1 from public.performances where id = p_performance_id for update;
  if not found then raise exception 'Performance does not exist'; end if;
  perform 1 from public.program_items
    where performance_id = p_performance_id and source_provider = 'nol' for update;
  select coalesce(jsonb_agg(to_jsonb(p) order by p.position, p.id), '[]'::jsonb)
    into v_before from public.program_items p
    where performance_id = p_performance_id and source_provider = 'nol';

  if p_expected is not null then
    select coalesce(jsonb_agg(to_jsonb(s) order by s.id), '[]'::jsonb) into v_expected
    from jsonb_to_recordset(p_expected) as s(
      id uuid, position integer, display_title text, composer_name text, work_id uuid,
      source_type text, confidence numeric, source_url text);
    select coalesce(jsonb_agg(to_jsonb(s) order by s.id), '[]'::jsonb) into v_actual
    from jsonb_to_recordset(v_before) as s(
      id uuid, position integer, display_title text, composer_name text, work_id uuid,
      source_type text, confidence numeric, source_url text);
    if v_actual is distinct from v_expected then return false; end if;
  end if;

  if exists (
    select 1 from jsonb_array_elements(p_items) i
    where jsonb_typeof(i) <> 'object' or coalesce(btrim(i->>'display_title'), '') = ''
      or coalesce(i->>'position', '') !~ '^[0-9]+$'
  ) or (select count(*) <> count(distinct i->>'position') from jsonb_array_elements(p_items) i) then
    raise exception 'Invalid or duplicate program positions';
  end if;

  select coalesce(jsonb_agg(jsonb_build_object(
    'id', coalesce(n.id, old.id, gen_random_uuid()),
    'performance_id', p_performance_id, 'source_provider', 'nol',
    'display_title', n.display_title, 'composer_name', n.composer_name,
    'work_id', n.work_id, 'source_type', coalesce(n.source_type, 'unknown'),
    'confidence', coalesce(n.confidence, 0), 'position', n.position,
    'source_url', n.source_url, 'created_at', coalesce(old.created_at, now())
  ) order by n.position), '[]'::jsonb) into v_after
  from jsonb_populate_recordset(null::public.program_items, p_items) n
  left join public.program_items old
    on old.performance_id = p_performance_id and old.source_provider = 'nol'
    and ((n.id is not null and old.id = n.id) or (n.id is null and old.position = n.position));

  if v_after = v_before then return true; end if;
  insert into public.provider_records(provider, entity_type, provider_id, payload)
  values ('nol_program_repair', 'program_snapshot',
    p_performance_id::text || ':' || md5(v_before::text || v_after::text),
    jsonb_build_object('before', v_before, 'after', v_after, 'parser_version', 'program-split-v1'))
  on conflict (provider, entity_type, provider_id) do nothing;

  delete from public.program_items where performance_id = p_performance_id and source_provider = 'nol';
  insert into public.program_items
    (id, performance_id, source_provider, display_title, composer_name, work_id,
     source_type, confidence, position, source_url, created_at)
  select id, performance_id, source_provider, display_title, composer_name, work_id,
    source_type, confidence, position, source_url, created_at
  from jsonb_populate_recordset(null::public.program_items, v_after);
  return true;
end;
$$;

revoke all on function public.replace_nol_program_items(uuid, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.replace_nol_program_items(uuid, jsonb, jsonb) to service_role;
notify pgrst, 'reload schema';
