begin;
create function pg_temp.reject_bundle(pid uuid,target jsonb,docs jsonb,ev jsonb,items jsonb) returns void
language plpgsql as $$
declare result jsonb;
begin
  begin
    result := public.publish_paddle_program_bundle(pid,target,docs,ev,items);
    if result->>'status' in ('published','unchanged') then raise exception 'TEST: unsafe bundle accepted'; end if;
  exception when others then
    if sqlerrm like 'TEST:%' then raise; end if;
  end;
end;
$$;
do $$
declare
  pid uuid := gen_random_uuid(); wid uuid; n integer;
  key text := gen_random_uuid()::text; urls text[];
  src jsonb; oc jsonb; rv jsonb; ref jsonb; matching jsonb;
  target jsonb; docs jsonb := '[]'::jsonb; ev jsonb; items jsonb; result jsonb; changed jsonb;
  legacy_ev jsonb; legacy_items jsonb;
begin
  if to_regprocedure('public.publish_paddle_program_bundle(uuid,jsonb,jsonb,jsonb,jsonb)') is null
  then raise exception 'TEST: missing bundle RPC'; end if;
  if has_function_privilege('anon','public.publish_paddle_program_bundle(uuid,jsonb,jsonb,jsonb,jsonb)','execute')
    or has_function_privilege('authenticated','public.publish_paddle_program_bundle(uuid,jsonb,jsonb,jsonb,jsonb)','execute')
    or not has_function_privilege('service_role','public.publish_paddle_program_bundle(uuid,jsonb,jsonb,jsonb,jsonb)','execute')
  then raise exception 'TEST: incorrect bundle grants'; end if;
  select id into wid from public.works limit 1;
  if wid is null then raise exception 'TEST: seed one work first'; end if;
  urls := array['https://kopis.or.kr/upload/'||key||'-cover.png','https://kopis.or.kr/upload/'||key||'-program.png'];
  insert into public.performances(id,title,starts_at,starts_on,ends_on,intro_image_urls)
    values(pid,'Bundle test',now(),'2026-10-22','2026-10-22',urls);
  target := jsonb_build_object('id',pid,'title','Bundle test','starts_on','2026-10-22','ends_on','2026-10-22','intro_image_urls',urls);
  ref := '{"context":"program","scope":"excerpt","composer":[{"line_id":"L000001","quote":"Test composer"}],"title":[{"line_id":"L000002","quote":"Test work"}],"catalogue":null,"key":null,"movements":[]}';
  for n in 1..2 loop
    src := jsonb_build_object('sha256',repeat(n::text,64),'bucket','test','object_key','originals/'||key||n,'source_url',urls[n],'performance_ids',jsonb_build_array(pid));
    oc := jsonb_build_object('source_sha256',src->>'sha256','bucket','test','source_object_key',src->>'object_key',
      'result_sha256',repeat((n+2)::text,64),'pipeline_version','paddle-test','status','text_extracted','processed_at',now());
    rv := jsonb_build_object('review_id',key||n,'version','paddle-partial-program-v1','method','reviewed_paddle_text',
      'source_sha256',src->>'sha256','bucket','test','document_sha256',oc->>'result_sha256',
      'response',jsonb_build_object('document_sha256',oc->>'result_sha256','status',case when n=1 then 'no_program_identified' else 'items_extracted' end,
        'items',case when n=1 then '[]'::jsonb else jsonb_build_array(ref) end));
    matching := jsonb_build_object('document_sha256',oc->>'result_sha256','validation_status','complete','warnings','[]'::jsonb,'source_warnings','[]'::jsonb,
      'items',case when n=1 then '[]'::jsonb else jsonb_build_array(jsonb_build_object('context','program','scope','excerpt','model_scope','excerpt','source_index',0,
        'scoped_work_id',wid,'identity_reason','composer_and_alias','publication_eligible',true,'evidence',ref,
        'fields',jsonb_build_object('composer','Test composer','title','Test work','catalogue',null,'movements','[]'::jsonb))) end);
    docs := docs || jsonb_build_array(jsonb_build_object('source',src,'ocr',oc,'review',rv,'matching',matching,
      'date_binding',case when n=1 then 'target' else 'absent' end,'live_sha256',src->>'sha256','source_checked_at',now()));
    insert into public.provider_records(provider,entity_type,provider_id,payload) values
      ('r2','source_archive',encode(sha256(convert_to(urls[n],'UTF8')),'hex'),src),
      ('paddleocr','ocr_result',key||n,oc),('paddle_review','program_selection',key||n,rv);
  end loop;
  ev := jsonb_build_object('publication_version','paddle-performance-bundle-v2','date_binding_version','concert-date-headings-v7','performance_date','2026-10-22');
  items := jsonb_build_array(jsonb_build_object('work_id',wid,'position',0,'display_title','Test work','composer_name','Test composer',
    'performed_scope','excerpt','scope_details','[]'::jsonb,'source_url',urls[2]));
  result := public.publish_paddle_program_bundle(pid,target,docs,ev,items);
  if result->>'status' <> 'published' then raise exception 'TEST: failed bundle publication: %',result; end if;
  if not exists(select 1 from public.program_items where performance_id=pid and work_id=wid and performed_scope='excerpt' and source_url=urls[2])
  then raise exception 'TEST: scope or source lost'; end if;
  result := public.publish_paddle_program_bundle(pid,target,docs,ev,items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: not idempotent'; end if;
  ev := jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v8"');
  result := public.publish_paddle_program_bundle(pid,target,docs,ev,items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v8 bundle contract not accepted'; end if;
  ev := jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v9"');
  result := public.publish_paddle_program_bundle(pid,target,docs,ev,items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v9 bundle contract not accepted'; end if;
  result := public.publish_paddle_program(pid,target,docs#>'{1,source}',docs#>'{1,ocr}',docs#>'{1,review}',ev,items);
  if result->>'status' <> 'existing_program_preserved' then raise exception 'TEST: legacy publisher can overwrite scoped bundle'; end if;
  if (select count(*) from public.provider_records where provider='paddle_review' and entity_type='bundle_publication' and payload->>'performance_id'=pid::text) <> 1
  then raise exception 'TEST: duplicate history'; end if;
  perform pg_temp.reject_bundle(pid,target,docs-0,ev,items);
  perform pg_temp.reject_bundle(pid,target,jsonb_set(docs,'{0,date_binding}','"absent"'),ev,items);
  perform pg_temp.reject_bundle(pid,target,jsonb_set(docs,'{0,live_sha256}','"changed"'),ev,items);
  perform pg_temp.reject_bundle(pid,target,jsonb_set(docs,'{0,source_checked_at}','"2000-01-01T00:00:00Z"'),ev,items);
  perform pg_temp.reject_bundle(pid,target,jsonb_set(docs,'{1,matching,source_warnings}','["multiple_dates"]'),ev,items);
  perform pg_temp.reject_bundle(pid,target,jsonb_set(docs,'{1,matching,items,0,scope}','"full_work"'),ev,items);
  perform pg_temp.reject_bundle(pid,target,jsonb_set(docs,'{1,matching,items,0,evidence,title,0,quote}','"forged"'),ev,items);
  perform pg_temp.reject_bundle(pid,target,docs,jsonb_set(ev,'{performance_date}','"2026-10-23"'),items);
  perform pg_temp.reject_bundle(pid,target,docs,jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v10"'),items);
  perform pg_temp.reject_bundle(pid,target,docs,ev,jsonb_set(items,'{0,performed_scope}','"full_work"'));
  perform pg_temp.reject_bundle(pid,target,docs,ev,jsonb_set(items,'{0,source_url}',to_jsonb(urls[1])));
  perform pg_temp.reject_bundle(pid,target,docs,ev,items||items);
  update public.provider_records set payload=jsonb_set(payload,'{sha256}','"changed"') where provider='r2' and provider_id=encode(sha256(convert_to(urls[1],'UTF8')),'hex');
  perform pg_temp.reject_bundle(pid,target,docs,ev,items);
  update public.provider_records set payload=docs#>'{0,source}' where provider='r2' and provider_id=encode(sha256(convert_to(urls[1],'UTF8')),'hex');
  insert into public.provider_records(provider,entity_type,provider_id,payload) values('paddleocr','ocr_result',key||'-new',
    (docs#>'{0,ocr}')||jsonb_build_object('result_sha256',repeat('e',64),'processed_at',now()+interval '1 second'));
  perform pg_temp.reject_bundle(pid,target,docs,ev,items);
  delete from public.provider_records where provider_id=key||'-new';

  -- A single image containing both full and partial works was vulnerable to
  -- an older full-work-only caller erasing the partial work on its next run.
  update public.performances set intro_image_urls=array[urls[2]] where id=pid;
  target := jsonb_set(target,'{intro_image_urls}',jsonb_build_array(urls[2]));
  docs := jsonb_build_array(jsonb_set(docs->1,'{date_binding}','"target"'));
  ref := jsonb_set(ref,'{scope}','"full_work"');
  rv := jsonb_set(docs#>'{0,review}','{response,items}',(docs#>'{0,review,response,items}')||jsonb_build_array(ref));
  update public.provider_records set payload=rv where provider='paddle_review' and entity_type='program_selection' and provider_id=rv->>'review_id';
  docs := jsonb_set(docs,'{0,review}',rv);
  changed := (docs#>'{0,matching,items,0}')||jsonb_build_object('scope','full_work','model_scope','full_work',
    'suggested_work_id',wid,'scoped_work_id',null,'reason','composer_and_alias','source_index',1,'evidence',ref);
  docs := jsonb_set(docs,'{0,matching,items}',(docs#>'{0,matching,items}')||jsonb_build_array(changed));
  items := items||jsonb_build_array((items->0)||jsonb_build_object('position',1,'performed_scope','full_work'));
  result := public.publish_paddle_program_bundle(pid,target,docs,ev,items);
  if result->>'status' <> 'published' then raise exception 'TEST: failed single-image mixed-scope bundle'; end if;
  legacy_items := jsonb_build_array((items->1)-'performed_scope'-'scope_details'-'source_url');
  legacy_ev := ev||jsonb_build_object('publication_version','paddle-partial-program-v1',
    'live_sha256',docs#>>'{0,source,sha256}','source_checked_at',now(),
    'matching',jsonb_set(docs#>'{0,matching}','{items}',jsonb_build_array(changed)));
  begin
    result := public.publish_paddle_program_v1(pid,target,docs#>'{0,source}',docs#>'{0,ocr}',rv,legacy_ev,legacy_items);
    if result->>'status' <> 'published' then raise exception 'TEST: legacy overwrite fixture did not reach publication'; end if;
    raise exception 'ROLLBACK_LEGACY_OVERWRITE';
  exception when others then
    if sqlerrm <> 'ROLLBACK_LEGACY_OVERWRITE' then raise; end if;
  end;
  result := public.publish_paddle_program(pid,target,docs#>'{0,source}',docs#>'{0,ocr}',rv,legacy_ev,legacy_items);
  if result->>'status' <> 'existing_program_preserved'
    or (select count(*) from public.program_items where performance_id=pid) <> 2
  then raise exception 'TEST: legacy full-work subset overwrote scoped bundle'; end if;
  update public.program_items set source_provider='manual' where performance_id=pid;
  result := public.publish_paddle_program_bundle(pid,target,docs,ev,items);
  if result->>'status' <> 'existing_program_preserved' then raise exception 'TEST: manual data overwritten'; end if;
  if (select count(*) from public.program_items where performance_id=pid and source_provider='manual') <> 2 then raise exception 'TEST: manual row lost'; end if;
end;
$$;
rollback;
select 'PASS: performance bundle, scopes, source/date binding, stale pointers, idempotence, history and manual preservation' as result;
