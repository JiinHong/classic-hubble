-- Synthetic fixtures roll back; no real observation or programme is modified.
begin;
do $$
declare
  pid uuid := gen_random_uuid();
  proposal_id uuid := gen_random_uuid();
  key text := 'revision-test-' || pid;
  url text := 'https://kopis.or.kr/upload/' || pid || '.png';
  src jsonb;
  sources jsonb;
  old jsonb;
  revised jsonb;
  proposal jsonb;
  result jsonb;
  target jsonb;
begin
  if to_regprocedure('public.revise_private_direct_reading(text,jsonb,jsonb,uuid,jsonb,jsonb)') is null
  then raise exception 'RED: atomic private correction RPC is missing'; end if;
  if has_function_privilege('anon', 'public.revise_private_direct_reading(text,jsonb,jsonb,uuid,jsonb,jsonb)', 'execute')
    or has_function_privilege('authenticated', 'public.revise_private_direct_reading(text,jsonb,jsonb,uuid,jsonb,jsonb)', 'execute')
    or not has_function_privilege('service_role', 'public.revise_private_direct_reading(text,jsonb,jsonb,uuid,jsonb,jsonb)', 'execute')
  then raise exception 'Unexpected revision privileges'; end if;
  insert into public.performances(id,title,starts_at,starts_on,ends_on,intro_image_urls)
    values(pid,'Rollback revision test',now(),'2026-10-22','2026-10-22',array[url]);
  src := jsonb_build_object('source_url',url,'performance_ids',jsonb_build_array(pid),'sha256',repeat('a',64),
    'bucket','synthetic-revision','object_key','originals/sha256/aa/' || repeat('a',64),'content_type','image/png','checked_at','2026-10-22T00:00:00Z');
  sources := jsonb_build_array(src - 'sha256' - 'bucket' - 'object_key');
  old := jsonb_build_object('source_sha256',repeat('a',64),'source_object_key',src->>'object_key','bucket','synthetic-revision',
    'method','chat_model_direct_image_reading','pipeline_version','codex-direct-vision-v1','status','text_extracted','coverage','complete',
    'reading_sha256',repeat('b',64),'result_sha256',repeat('e',64),'result_object_key','extractions/sha256/ee/' || repeat('e',64));
  revised := old || jsonb_build_object('reading_sha256',repeat('c',64),'result_sha256',repeat('d',64),
    'result_object_key','extractions/sha256/dd/' || repeat('d',64),'revision',jsonb_build_object('proposal_id',proposal_id,'previous_reading_sha256',repeat('b',64)));
  proposal := jsonb_build_object('source_sha256',repeat('a',64),'bucket','synthetic-revision','status','pending_revision_workflow',
    'supersedes_reading_sha256',repeat('b',64),'corrected_reading_sha256',repeat('c',64));
  insert into public.provider_records(provider,entity_type,provider_id,payload) values
    ('r2','source_archive',encode(sha256(convert_to(url,'UTF8')),'hex'),src),
    ('codex_vision','direct_reading',key,old);
  insert into public.provider_records(id,provider,entity_type,provider_id,payload)
    values(proposal_id,'codex_vision','direct_reading_correction_proposal',key,proposal);

  result := public.revise_private_direct_reading(key,old || '{"coverage":"partial"}',revised,proposal_id,proposal,sources);
  if result->>'status' <> 'stale' then raise exception 'Stale expected reading accepted'; end if;
  result := public.revise_private_direct_reading(key,old,revised,proposal_id,proposal || '{"status":"changed"}',sources);
  if result->>'status' <> 'stale' then raise exception 'Stale proposal accepted'; end if;
  result := public.revise_private_direct_reading(key,old,revised,proposal_id,proposal,'[]');
  if result->>'status' <> 'stale' then raise exception 'Changed sources accepted'; end if;
  begin
    perform public.revise_private_direct_reading(key,old,revised || '{"bucket":"other"}',proposal_id,proposal,sources);
    raise exception 'TEST: identity mutation accepted';
  exception when others then if sqlerrm <> 'Invalid correction evidence' then raise; end if; end;

  result := public.revise_private_direct_reading(key,old,revised,proposal_id,proposal,sources);
  if result->>'status' <> 'revised' then raise exception 'Promotion failed: %', result; end if;
  if (select payload from public.provider_records where provider='codex_vision' and entity_type='direct_reading' and provider_id=key) is distinct from revised
    or not exists(select 1 from public.provider_records where provider='codex_vision' and entity_type='direct_reading_revision'
      and provider_id=proposal_id::text and payload->'before'=old and payload->'after'=revised)
  then raise exception 'Active pointer/history mismatch'; end if;
  result := public.revise_private_direct_reading(key,old,revised,proposal_id,proposal,sources);
  if result->>'status' <> 'unchanged' then raise exception 'Repeat revision not idempotent'; end if;
  result := public.revise_private_direct_reading(key,old,revised || '{"stored_at":"2026-10-23T02:00:00Z"}',proposal_id,proposal,sources);
  if result->>'status' <> 'unchanged' then raise exception 'Concurrent timestamp prevents idempotence'; end if;

  target := jsonb_build_object('id',pid,'title','Rollback revision test','starts_on','2026-10-22','ends_on','2026-10-22','intro_image_urls',jsonb_build_array(url));
  result := public.publish_direct_vision_program(pid,target,src,old,'{}','[]');
  if result->>'status' <> 'stale' then raise exception 'Old reading still usable for publication'; end if;

  -- A later publication forbids silent private revision, even if public rows were removed.
  insert into public.provider_records(provider,entity_type,provider_id,payload)
    values('codex_vision','program_publication',key,jsonb_build_object('source',src));
  proposal_id := gen_random_uuid();
  proposal := proposal || jsonb_build_object('supersedes_reading_sha256',repeat('c',64),'corrected_reading_sha256',repeat('f',64));
  insert into public.provider_records(id,provider,entity_type,provider_id,payload)
    values(proposal_id,'codex_vision','direct_reading_correction_proposal',key || '-2',proposal);
  old := revised;
  revised := old || jsonb_build_object('reading_sha256',repeat('f',64),'revision',jsonb_build_object('proposal_id',proposal_id,'previous_reading_sha256',repeat('c',64)));
  result := public.revise_private_direct_reading(key,old,revised,proposal_id,proposal,sources);
  if result->>'status' <> 'published_source_requires_reconciliation'
    or (select payload from public.provider_records where provider='codex_vision' and entity_type='direct_reading' and provider_id=key) is distinct from old
  then raise exception 'Previously published source silently revised'; end if;
end $$;
rollback;
select 'PASS: private revision, history, CAS, source/proposal identity, idempotence, stale publication and published-source refusal' as result;
