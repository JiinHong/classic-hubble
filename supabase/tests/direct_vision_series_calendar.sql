-- All data is synthetic and rollback-only. Calendar cells are read by column.
begin;
do $$
declare
  texts text[] := array['피아니스트 김태형 II','2026. 9. 17 (목) 19:30','Program',
    '피아니스트 김태형의 프로젝트 II','루트비히 판 베토벤','피아노 소나타 제25번 G장조, Op.79','Artist',
    '피아니스트 김태형','<위대한 작곡가> 시리즈 연간 공연 일정',
    '3 / 12','바이올리니스트 유다윤','첼리스트 정우찬','9 / 10','바이올리니스트 한수진','J.S.바흐',
    '9 / 17','피아니스트 김태형','루트비히 판 베토벤','11 / 12','피아니스트 문지영','프란츠 슈베르트','금호문화재단'];
  labels jsonb; r jsonb; item jsonb; match jsonb; body text; sha text; proof jsonb; bad jsonb; variants jsonb[];
  d date := '2026-09-17';
  pid uuid := gen_random_uuid(); wid uuid; url text := 'https://kopis.or.kr/upload/series-test-'||pid::text||'.png';
  src jsonb; rd jsonb; target jsonb; ev jsonb; output jsonb; result jsonb;
begin
  if has_function_privilege('anon','public.direct_series_program_proof(text,text,date,jsonb)','execute')
    or has_function_privilege('authenticated','public.direct_series_program_proof(text,text,date,jsonb)','execute')
    or not has_function_privilege('service_role','public.direct_series_program_proof(text,text,date,jsonb)','execute')
  then raise exception 'Unexpected calendar proof grants'; end if;
  select jsonb_agg(jsonb_build_object('page_index',0,'text',value) order by ord) into labels
    from unnest(texts) with ordinality as t(value,ord);
  item := '{"context":"program","scope":"full_work","composer":[{"line_id":"L000004","quote":"루트비히 판 베토벤"}],"title":[{"line_id":"L000005","quote":"피아노 소나타 제25번"}],"catalogue":[{"line_id":"L000005","quote":"Op.79"}],"key":[{"line_id":"L000005","quote":"G장조"}],"movements":[]}';
  match := jsonb_build_array(jsonb_build_object('evidence',item,'context','program','scope','full_work',
    'fields',jsonb_build_object('title','피아노 소나타 제25번','catalogue','Op.79','key','G장조','composer','루트비히 판 베토벤','movements','[]'::jsonb)));
  r := jsonb_build_object('lines',labels,'coverage','complete','status','text_extracted','extraction_status','items_extracted','items',jsonb_build_array(item));
  body := r::text; sha := encode(sha256(convert_to(body,'UTF8')),'hex');
  proof := public.direct_series_program_proof(body,sha,d,match);
  if proof is null or proof->>'performance_date'<>'2026-09-17' or proof->>'end_line'<>'6'
    or proof is distinct from public.direct_series_program_proof(body,sha,d,null)
  then raise exception 'Verified main programme with correctly bound calendar did not pass: %', proof; end if;
  if public.direct_series_program_proof(body,repeat('a',64),d,match) is not null
    or public.direct_series_program_proof(body,sha,d-7,match) is not null
    or public.direct_series_program_proof(body,sha,d,'[]') is not null
    or public.direct_series_program_proof(body,sha,d,jsonb_set(match,'{0,fields,title}','"Other"')) is not null
    or public.direct_series_program_proof(body,sha,d,jsonb_set(match,'{0,evidence,title,0,line_id}','"L000017"')) is not null
  then raise exception 'Hash, date, or submitted evidence mismatch was accepted'; end if;
  variants := array[
    jsonb_set(r,'{lines,1,text}','"2026. 9. 17 (금) 19:30"'), jsonb_set(r,'{lines,1,text}','"예매 2026. 9. 17 (목) 19:30"'),
    jsonb_set(r,'{lines,7,text}','"2026. 9. 18 (금) 19:30"'), jsonb_set(r,'{lines,8,text}','"다른 프로그램"'),
    jsonb_set(r,'{lines,9,text}','"2 / 30"'), jsonb_set(r,'{lines,12,text}','"9 / 17"'),
    jsonb_set(r,'{lines,15,text}','"9 / 19"'), jsonb_set(r,'{lines,16,text}','"피아니스트 다른이"'),
    jsonb_set(r,'{lines,17,text}','"프란츠 슈베르트"'), jsonb_set(r,'{lines,18,text}','"11 / 12 (목) 19:30"'),
    jsonb_set(r,'{lines,21,text}','"Program"'), jsonb_set(r,'{lines,2,page_index}','1'),
    jsonb_set(r,'{items,0,composer,0,line_id}','"L000017"'),jsonb_set(r,'{items,0,title,0,quote}','"전원"'),
    jsonb_set(r,'{items,0,scope}','"movement"'),jsonb_set(r,'{coverage}','"partial"'),
    jsonb_set(r,'{items}',jsonb_build_array(item,item))
  ];
  foreach bad in array variants loop
    body := bad::text; sha := encode(sha256(convert_to(body,'UTF8')),'hex');
    if public.direct_series_program_proof(body,sha,d,null) is not null then
      raise exception 'Unbound calendar or evidence was accepted: %',bad; end if;
  end loop;
  -- Run the real, locked transaction and check that neither replay nor a forged
  -- match can turn this date-specific proof into a different public programme.
  body := r::text; sha := encode(sha256(convert_to(body,'UTF8')),'hex');
  select id into strict wid from public.works limit 1;
  insert into public.performances(id,title,starts_at,starts_on,ends_on,intro_image_urls)
    values(pid,'Rollback-only calendar test',now(),d,d,array[url]);
  target := jsonb_build_object('id',pid,'title','Rollback-only calendar test','starts_on',d,'ends_on',d,'intro_image_urls',jsonb_build_array(url));
  src := jsonb_build_object('source_url',url,'performance_ids',jsonb_build_array(pid),'sha256',repeat('a',64),'bucket','private-test','object_key','originals/test');
  rd := jsonb_build_object('pipeline_version','codex-direct-vision-v1','source_sha256',repeat('a',64),'source_object_key','originals/test','bucket','private-test',
    'method','chat_model_direct_image_reading','reading_sha256',sha,'coverage','complete','status','text_extracted');
  insert into public.provider_records(provider,entity_type,provider_id,payload) values
    ('r2','source_archive',encode(sha256(convert_to(url,'UTF8')),'hex'),src),('codex_vision','direct_reading',pid::text,rd);
  match := jsonb_build_array(match->0||jsonb_build_object('suggested_work_id',wid,'reason','composer_and_catalogue'));
  output := jsonb_build_array(jsonb_build_object('work_id',wid,'position',0,'display_title','피아노 소나타 제25번 Op.79','composer_name','루트비히 판 베토벤'));
  ev := jsonb_build_object('publication_version','direct-vision-series-calendar-v1','performance_date',d,'live_sha256',repeat('a',64),
    'reading_sha256',sha,'source_checked_at',now(),'matching',jsonb_build_object('complete',true,'validation_status','complete',
    'catalogue_sha256','fixture','items',match,'source_warnings','[]'::jsonb),'series_program',proof,'series_reading_utf8',body);
  begin
    perform public.publish_direct_vision_program(pid,target,src,rd,jsonb_set(ev,'{series_program,end_line}','18'),output);
    raise exception 'TEST: modified boundaries accepted';
  exception when raise_exception then if sqlerrm<>'Invalid annual programme evidence' then raise; end if; end;
  begin
    perform public.publish_direct_vision_program(pid,target,src,rd,jsonb_set(ev,'{matching,items,0,fields,title}','"Other"'),output);
    raise exception 'TEST: modified fields accepted';
  exception when raise_exception then if sqlerrm<>'Invalid annual programme evidence' then raise; end if; end;
  begin
    perform public.publish_direct_vision_program(pid,target,src,rd,jsonb_set(ev,'{publication_version}','"direct-vision-single-source-v1"'),output);
    raise exception 'TEST: series proof accepted on legacy path';
  exception when raise_exception then if sqlerrm<>'Unexpected annual programme evidence' then raise; end if; end;
  result := public.publish_direct_vision_program(pid,target,src,rd,ev,output);
  if result->>'status'<>'published' then raise exception 'Valid proof not published: %',result; end if;
  result := public.publish_direct_vision_program(pid,target,src,rd,ev,output);
  if result->>'status'<>'unchanged' or (select count(*) from public.program_items where performance_id=pid)<>1 then raise exception 'Replay unsafe: %',result; end if;
  if not exists(select from public.provider_records where provider='codex_vision' and entity_type='program_publication' and payload->>'performance_id'=pid::text
    and payload#>'{evaluation,series_program}'=proof and not ((payload->'evaluation') ? 'series_reading_utf8'))
  then raise exception 'Compact proof not preserved'; end if;
end $$;
rollback;
select 'PASS: complete four-column series grid, original bytes, date, performer, composer, quotes and negative controls' as result;
