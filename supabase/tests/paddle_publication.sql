begin;
do $$
declare
  pid uuid := gen_random_uuid();
  wid uuid;
  url text := 'https://kopis.or.kr/upload/paddle-test-' || pid::text || '.png';
  src jsonb; oc jsonb; rv jsonb; ev jsonb; target jsonb; items jsonb; result jsonb;
  ref jsonb := '{"context":"program","scope":"full_work","composer":[{"line_id":"L000001","quote":"Test composer"}],"title":[{"line_id":"L000002","quote":"Test work"}],"catalogue":null,"key":null,"movements":[]}';
  key text := 'paddle-test-' || pid::text;
  date_version text;
begin
  if to_regprocedure('public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)') is null then
    raise exception 'TEST: Paddle publication RPC is missing';
  end if;
  if has_function_privilege('anon','public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)','execute')
    or has_function_privilege('authenticated','public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)','execute')
    or not has_function_privilege('service_role','public.publish_paddle_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)','execute')
  then raise exception 'TEST: incorrect grants'; end if;
  select id into wid from public.works limit 1;
  insert into public.performances(id,title,starts_at,starts_on,ends_on,intro_image_urls)
    values(pid,'Paddle test',now(),'2026-10-22','2026-10-22',array[url]);
  target := jsonb_build_object('id',pid,'title','Paddle test','starts_on','2026-10-22','ends_on','2026-10-22','intro_image_urls',array[url]);
  src := jsonb_build_object('sha256',repeat('a',64),'bucket','test','object_key','originals/test','source_url',url,'performance_ids',jsonb_build_array(pid));
  oc := jsonb_build_object('source_sha256',repeat('a',64),'bucket','test','source_object_key','originals/test','result_sha256',repeat('b',64),'pipeline_version','paddle-test','status','text_extracted','processed_at',now());
  rv := jsonb_build_object('review_id',key,'method','reviewed_paddle_text','version','paddle-partial-program-v1','source_sha256',repeat('a',64),'document_sha256',repeat('b',64),'bucket','test','response',jsonb_build_object('document_sha256',repeat('b',64),'items',jsonb_build_array(ref)));
  ev := jsonb_build_object('publication_version','paddle-partial-program-v1','date_binding_version','performance-date-binding-v5','performance_date','2026-10-22','live_sha256',repeat('a',64),'source_checked_at',now(),'matching',jsonb_build_object('document_sha256',repeat('b',64),'validation_status','complete','source_warnings','[]'::jsonb,'warnings','[]'::jsonb,'items',jsonb_build_array(jsonb_build_object('context','program','scope','full_work','source_index',0,'suggested_work_id',wid,'reason','composer_and_alias','publication_eligible',true,'fields',jsonb_build_object('composer','Test composer','title','Test work','catalogue',null),'evidence',ref))));
  ev := ev || jsonb_build_object('date_binding_version','concert-date-headings-v5');
  items := jsonb_build_array(jsonb_build_object('work_id',wid,'position',0,'display_title','Test work','composer_name','Test composer'));
  insert into public.provider_records(provider,entity_type,provider_id,payload) values
    ('r2','source_archive',encode(sha256(convert_to(url,'UTF8')),'hex'),src),
    ('paddleocr','ocr_result',key,oc),('paddle_review','program_selection',key,rv);
  result := public.publish_paddle_program(pid,target,src,oc,rv,ev,items);
  if result->>'status' <> 'published' or (select program_status::text from public.performances where id=pid) <> 'partially_confirmed' then raise exception 'TEST: did not publish partially'; end if;
  result := public.publish_paddle_program(pid,target,src,oc,rv,ev,items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: not idempotent'; end if;
  if (select count(*) from public.program_items where performance_id=pid) <> 1 then raise exception 'TEST: duplicate rows'; end if;
  -- Version updates must not weaken normalized date, warning, or saved-evidence checks.
  result := public.publish_paddle_program(pid,target,src,oc,rv,
    jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v6"'),items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v6 contract not accepted'; end if;
  result := public.publish_paddle_program(pid,target,src,oc,rv,
    jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v7"'),items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v7 contract not accepted'; end if;
  result := public.publish_paddle_program(pid,target,src,oc,rv,
    jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v8"'),items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v8 contract not accepted'; end if;
  result := public.publish_paddle_program(pid,target,src,oc,rv,
    jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v9"'),items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v9 contract not accepted'; end if;
  result := public.publish_paddle_program(pid,target,src,oc,rv,
    jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v10"'),items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v10 contract not accepted'; end if;
  result := public.publish_paddle_program(pid,target,src,oc,rv,
    jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v11"'),items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v11 contract not accepted'; end if;
  result := public.publish_paddle_program(pid,target,src,oc,rv,
    jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v12"'),items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v12 contract not accepted'; end if;
  result := public.publish_paddle_program(pid,target,src,oc,rv,
    jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v13"'),items);
  if result->>'status' <> 'unchanged' then raise exception 'TEST: v13 contract not accepted'; end if;
  foreach date_version in array array['', 'concert-date-headings-v4', 'concert-date-headings-v14'] loop
    begin
      perform public.publish_paddle_program(pid,target,src,oc,rv,
        jsonb_set(ev,'{date_binding_version}',to_jsonb(date_version)),items);
      raise exception 'TEST: invalid date version accepted';
    exception when others then
      if sqlerrm <> 'Incomplete Paddle publication evidence' then raise; end if;
    end;
  end loop;
  ev := jsonb_set(ev,'{date_binding_version}','"concert-date-headings-v13"');
  begin
    perform public.publish_paddle_program(pid,target,src,oc,rv,jsonb_set(ev,'{performance_date}','"2026-10-23"'),items);
    raise exception 'TEST: accepted wrong date';
  exception when others then if sqlerrm like 'TEST:%' then raise; end if; end;
  begin
    perform public.publish_paddle_program(pid,target,src,oc,rv,jsonb_set(ev,'{matching,source_warnings}','["unresolved_performance_dates"]'),items);
    raise exception 'TEST: accepted date warning';
  exception when others then if sqlerrm like 'TEST:%' then raise; end if; end;
  begin
    perform public.publish_paddle_program(pid,target,src,oc,rv,jsonb_set(ev,'{matching,items,0,scope}','"excerpt"'),items);
    raise exception 'TEST: accepted excerpt';
  exception when others then if sqlerrm like 'TEST:%' then raise; end if; end;
  begin
    perform public.publish_paddle_program(pid,target,src,oc,rv,jsonb_set(ev,'{matching,items,0,evidence,title,0,quote}','"forged"'),items);
    raise exception 'TEST: accepted forged evidence';
  exception when others then if sqlerrm like 'TEST:%' then raise; end if; end;
  begin
    perform public.publish_paddle_program(pid,target,src,oc,rv,ev,jsonb_set(items,'{0,display_title}','"forged"'));
    raise exception 'TEST: accepted forged label';
  exception when others then if sqlerrm like 'TEST:%' then raise; end if; end;
  result := public.publish_paddle_program(pid,target,src,oc,jsonb_set(rv,'{method}','"renamed_vision"'),ev,items);
  if result->>'status' <> 'stale' then raise exception 'TEST: stale review accepted'; end if;
  insert into public.provider_records(provider,entity_type,provider_id,payload)
    values('paddleocr','ocr_result',key||'-new',oc||jsonb_build_object('result_sha256',repeat('c',64),'processed_at',now()+interval '1 second'));
  result := public.publish_paddle_program(pid,target,src,oc,rv,ev,items);
  if result->>'status' <> 'stale' then raise exception 'TEST: superseded OCR accepted'; end if;
  delete from public.provider_records where provider_id=key||'-new';
  update public.program_items set source_provider='manual' where performance_id=pid;
  result := public.publish_paddle_program(pid,target,src,oc,rv,ev,items);
  if result->>'status' <> 'existing_program_preserved' then raise exception 'TEST: manual programme overwritten'; end if;
  if not exists(select 1 from public.program_items where performance_id=pid and source_provider='manual') then raise exception 'TEST: manual row lost'; end if;
end;
$$;
rollback;
select 'PASS: Paddle partial publication, permissions, dates, scope, evidence, idempotence, stale OCR and manual preservation' as result;
