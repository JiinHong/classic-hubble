-- All fixtures and mutations roll back. Run after the publication migration.
begin;
do $$
declare
  pid uuid := gen_random_uuid();
  wid uuid;
  source_url text := 'https://kopis.or.kr/upload/atomic-test-' || pid::text || '.png';
  src jsonb;
  rd jsonb;
  ev jsonb;
  items jsonb;
  target jsonb;
  result jsonb;
  first_id uuid;
begin
  if has_function_privilege('anon', 'public.publish_direct_vision_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb)', 'execute')
    or has_function_privilege('authenticated', 'public.publish_direct_vision_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb)', 'execute')
    or not has_function_privilege('service_role', 'public.publish_direct_vision_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb)', 'execute')
  then raise exception 'Unexpected function grants'; end if;
  select id into strict wid from public.works limit 1;
  insert into public.performances(id, title, starts_at, starts_on, ends_on, intro_image_urls)
    values(pid, 'Rollback-only test', now(), '2026-10-22', '2026-10-22', array[source_url]);
  target := jsonb_build_object('id', pid, 'title', 'Rollback-only test',
    'starts_on', '2026-10-22', 'ends_on', '2026-10-22', 'intro_image_urls', jsonb_build_array(source_url));
  src := jsonb_build_object('source_url', source_url, 'performance_ids', jsonb_build_array(pid),
    'sha256', repeat('a',64), 'bucket', 'synthetic-test', 'object_key', 'originals/test');
  rd := jsonb_build_object('source_sha256', repeat('a',64), 'bucket', 'synthetic-test',
    'pipeline_version', 'codex-direct-vision-v1', 'coverage', 'complete', 'status', 'text_extracted',
    'method', 'chat_model_direct_image_reading', 'source_object_key', 'originals/test', 'reading_sha256', repeat('b',64));
  insert into public.provider_records(provider, entity_type, provider_id, payload) values
    ('r2', 'source_archive', encode(sha256(convert_to(source_url, 'UTF8')), 'hex'), src),
    ('codex_vision', 'direct_reading', pid::text, rd);
  items := jsonb_build_array(jsonb_build_object('work_id', wid, 'position', 0,
    'display_title', 'Test work Op. 1', 'composer_name', 'Test composer'));
  ev := jsonb_build_object('publication_version', 'direct-vision-single-source-v1',
    'performance_date', '2026-10-22',
    'reading_sha256', repeat('b',64), 'live_sha256', repeat('a',64), 'source_checked_at', now(),
    'matching', jsonb_build_object('complete', true, 'validation_status', 'complete',
      'catalogue_sha256', 'test', 'source_warnings', '[]'::jsonb,
      'items', jsonb_build_array(jsonb_build_object('context', 'program', 'scope', 'full_work',
        'suggested_work_id', wid, 'reason', 'composer_and_catalogue',
        'fields', jsonb_build_object('title', 'Test work', 'catalogue', 'Op. 1', 'composer', 'Test composer')))));

  result := public.publish_direct_vision_program(pid, target, src, rd, ev, items);
  if result->>'status' <> 'published' then raise exception 'First publication failed: %', result; end if;
  select id into first_id from public.program_items where performance_id = pid;
  result := public.publish_direct_vision_program(pid, target, src, rd, ev, items);
  if result->>'status' <> 'unchanged' or (select count(*) from public.program_items where performance_id = pid) <> 1
    or (select id from public.program_items where performance_id = pid) <> first_id
  then raise exception 'Duplicate publication changed rows'; end if;

  result := public.publish_direct_vision_program(pid, target || '{"title":"changed"}', src, rd, ev, items);
  if result->>'status' <> 'stale' then raise exception 'Stale performance was accepted'; end if;
  result := public.publish_direct_vision_program(pid, target, src || '{"sha256":"changed"}', rd, ev, items);
  if result->>'status' <> 'stale' then raise exception 'Replaced source was accepted'; end if;
  result := public.publish_direct_vision_program(pid, target, src, rd || '{"reading_sha256":"changed"}', ev, items);
  if result->>'status' <> 'stale' then raise exception 'Changed reading was accepted'; end if;

  -- Python grounds the transcription; SQL requires its normalized date to match
  -- the locked performance, including the year. Neither a missing nor wrong
  -- evaluation date may reuse an otherwise valid publication payload.
  begin
    perform public.publish_direct_vision_program(pid, target, src, rd, ev - 'performance_date', items);
    raise exception 'TEST: missing date unexpectedly accepted';
  exception when others then
    if sqlerrm <> 'Incomplete publication evidence' then raise; end if;
  end;
  begin
    perform public.publish_direct_vision_program(pid, target, src, rd,
      jsonb_set(ev, '{performance_date}', '"2025-10-22"'), items);
    raise exception 'TEST: wrong year unexpectedly accepted';
  exception when others then
    if sqlerrm <> 'Incomplete publication evidence' then raise; end if;
  end;
  begin
    perform public.publish_direct_vision_program(pid, target, src, rd,
      jsonb_set(ev, '{performance_date}', '"2026-10-23"'), items);
    raise exception 'TEST: wrong day unexpectedly accepted';
  exception when others then
    if sqlerrm <> 'Incomplete publication evidence' then raise; end if;
  end;

  begin
    perform public.publish_direct_vision_program(pid, target, src, rd,
      jsonb_set(ev, '{matching,items,0,scope}', '"excerpt"'), items);
    raise exception 'TEST: excerpt unexpectedly accepted';
  exception when others then
    if sqlerrm <> 'Program differs from matching evidence' then raise; end if;
  end;
  begin
    perform public.publish_direct_vision_program(pid, target, src, rd, ev,
      jsonb_set(items, '{0,display_title}', '"invented"'));
    raise exception 'TEST: invented label unexpectedly accepted';
  exception when others then
    if sqlerrm <> 'Program differs from matching evidence' then raise; end if;
  end;

  insert into public.program_items(performance_id, display_title, source_provider, position)
    values(pid, 'Existing NOL work', 'nol', 0);
  result := public.publish_direct_vision_program(pid, target, src, rd, ev, items);
  if result->>'status' <> 'existing_program_preserved'
    or (select count(*) from public.program_items where performance_id = pid) <> 2
  then raise exception 'Existing provider data was changed'; end if;
end $$;
rollback;
select 'PASS: permissions, publication, idempotence, stale source/reading/performance, date, scope, evidence, provider preservation' as result;
