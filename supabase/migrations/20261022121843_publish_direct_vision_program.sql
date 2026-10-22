-- Restricted to complete single-image/single-date observations. Other providers win.
create or replace function public.publish_direct_vision_program(
  p_performance_id uuid, p_expected_performance jsonb, p_source jsonb,
  p_reading jsonb, p_evaluation jsonb, p_items jsonb
) returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare
  v_performance public.performances;
  v_source jsonb;
  v_reading jsonb;
  v_before jsonb;
  v_after jsonb;
  v_key text;
  v_count integer;
begin
  select * into v_performance from public.performances
    where id = p_performance_id for update;
  if not found then return jsonb_build_object('status', 'missing_performance', 'items', 0); end if;
  if jsonb_build_object('id', v_performance.id, 'title', v_performance.title,
      'starts_on', v_performance.starts_on, 'ends_on', v_performance.ends_on,
      'intro_image_urls', v_performance.intro_image_urls) is distinct from p_expected_performance
    or cardinality(v_performance.intro_image_urls) <> 1
    or v_performance.starts_on is null
    or v_performance.starts_on is distinct from v_performance.ends_on
    or v_performance.intro_image_urls[1] is distinct from p_source->>'source_url'
  then return jsonb_build_object('status', 'stale', 'items', 0); end if;

  select payload into v_source from public.provider_records
    where provider = 'r2' and entity_type = 'source_archive'
      and provider_id = encode(sha256(convert_to(p_source->>'source_url', 'UTF8')), 'hex')
    for update;
  if not found or v_source is distinct from p_source
    or not coalesce(v_source->'performance_ids' ? p_performance_id::text, false)
  then return jsonb_build_object('status', 'stale', 'items', 0); end if;

  select payload into v_reading from public.provider_records
    where provider = 'codex_vision' and entity_type = 'direct_reading'
      and payload->>'source_sha256' = p_source->>'sha256'
      and payload->>'bucket' = p_source->>'bucket'
      and payload->>'pipeline_version' = 'codex-direct-vision-v1'
    for update;
  if not found or v_reading is distinct from p_reading
    or p_reading->>'coverage' is distinct from 'complete'
    or p_reading->>'status' is distinct from 'text_extracted'
    or p_reading->>'method' is distinct from 'chat_model_direct_image_reading'
    or p_reading->>'source_object_key' is distinct from p_source->>'object_key'
  then return jsonb_build_object('status', 'stale', 'items', 0); end if;

  if p_evaluation->>'publication_version' is distinct from 'direct-vision-single-source-v1'
    or p_evaluation->>'performance_date' is distinct from v_performance.starts_on::text
    or p_evaluation->>'reading_sha256' is distinct from p_reading->>'reading_sha256'
    or p_evaluation->>'live_sha256' is distinct from p_source->>'sha256'
    or (p_evaluation->>'source_checked_at')::timestamptz < now() - interval '5 minutes'
    or (p_evaluation->>'source_checked_at')::timestamptz > now() + interval '1 minute'
    or p_evaluation->>'source_checked_at' is null
    or p_evaluation#>>'{matching,complete}' is distinct from 'true'
    or p_evaluation#>>'{matching,validation_status}' is distinct from 'complete'
    or p_evaluation#>'{matching,source_warnings}' is distinct from '[]'::jsonb
    or jsonb_typeof(p_items) is distinct from 'array'
    or jsonb_array_length(p_items) not between 1 and 200
  then raise exception 'Incomplete publication evidence'; end if;

  -- The service cannot submit unrelated IDs/labels in place of validated matches.
  select coalesce(jsonb_agg(jsonb_build_object(
    'work_id', m->>'suggested_work_id', 'position', position - 1,
    'display_title', concat_ws(' ', nullif(m#>>'{fields,title}', ''), nullif(m#>>'{fields,catalogue}', '')),
    'composer_name', m#>>'{fields,composer}') order by position), '[]'::jsonb)
    into v_after
  from (
    select m, row_number() over (order by ordinal) position
    from jsonb_array_elements(p_evaluation#>'{matching,items}') with ordinality as x(m, ordinal)
    where m->>'context' = 'program'
  ) matched;
  if v_after is distinct from p_items or exists (
    select 1 from jsonb_array_elements(p_evaluation#>'{matching,items}') m
    where m->>'context' = 'program' and (
      m->>'scope' is distinct from 'full_work' or m->>'suggested_work_id' is null
      or m->>'reason' not in ('composer_and_alias', 'composer_and_catalogue', 'unique_distinctive_title', 'surname_and_distinctive_title')
    )
  ) then raise exception 'Program differs from matching evidence'; end if;

  perform 1 from public.program_items where performance_id = p_performance_id for update;
  if exists (select 1 from public.program_items where performance_id = p_performance_id
      and source_provider <> 'codex_vision')
    or (v_performance.program_status = 'confirmed'
      and not exists (select 1 from public.program_items where performance_id = p_performance_id
        and source_provider = 'codex_vision'))
  then return jsonb_build_object('status', 'existing_program_preserved', 'items', 0); end if;

  v_count := jsonb_array_length(p_items);
  v_key := p_performance_id::text || ':' || md5(jsonb_build_object(
    'source', p_source->>'sha256', 'reading', p_reading->>'reading_sha256',
    'items', p_items, 'version', p_evaluation->>'publication_version',
    'catalogue', p_evaluation#>>'{matching,catalogue_sha256}')::text);
  if exists (select 1 from public.provider_records where provider = 'codex_vision'
      and entity_type = 'program_publication' and provider_id = v_key)
    and (select coalesce(jsonb_agg(jsonb_build_object('work_id', work_id,
      'position', position, 'display_title', display_title, 'composer_name', composer_name)
      order by position), '[]'::jsonb) from public.program_items
      where performance_id = p_performance_id and source_provider = 'codex_vision') = p_items
  then return jsonb_build_object('status', 'unchanged', 'items', v_count); end if;

  select coalesce(jsonb_agg(to_jsonb(i) order by position), '[]'::jsonb) into v_before
    from public.program_items i where performance_id = p_performance_id and source_provider = 'codex_vision';
  insert into public.provider_records(provider, entity_type, provider_id, payload)
    values ('codex_vision', 'program_publication', v_key, jsonb_build_object(
      'performance_id', p_performance_id, 'before', v_before, 'before_performance', to_jsonb(v_performance),
      'after', p_items, 'source', p_source, 'reading', p_reading, 'evaluation', p_evaluation))
    on conflict (provider, entity_type, provider_id) do nothing;
  delete from public.program_items where performance_id = p_performance_id and source_provider = 'codex_vision';
  insert into public.program_items(performance_id, work_id, display_title, composer_name,
      source_type, confidence, position, source_provider, source_url)
    select p_performance_id, (i->>'work_id')::uuid, i->>'display_title', i->>'composer_name',
      'ocr', 0, (i->>'position')::integer, 'codex_vision', p_source->>'source_url'
    from jsonb_array_elements(p_items) i;
  update public.performances set program_status = 'confirmed',
    program_source_url = p_source->>'source_url', program_image_urls = intro_image_urls,
    program_source_updated_at = (p_evaluation->>'source_checked_at')::timestamptz
    where id = p_performance_id;
  return jsonb_build_object('status', 'published', 'items', v_count);
end;
$$;
revoke all on function public.publish_direct_vision_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb) from public, anon, authenticated;
grant execute on function public.publish_direct_vision_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb) to service_role;
notify pgrst, 'reload schema';
