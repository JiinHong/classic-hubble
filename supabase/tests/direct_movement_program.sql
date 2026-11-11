begin;
do $test$
declare
  day date:='2026-10-22'; pid uuid:=gen_random_uuid(); composer uuid; work uuid; kid text:='test-'||pid;
  url text:='https://kopis.or.kr/upload/'||pid||'.jpg'; orig text:=repeat('a',64); stamp text:='2026. 10. 22 TUR 7:30 PM Fixture Hall';
  reading jsonb; envelope jsonb; cite jsonb; ref jsonb; entry jsonb; docs jsonb; src jsonb; ptr jsonb; d jsonb;
  raw text; digest_raw text; result jsonb; ready jsonb; expected jsonb; saved_id uuid; candidate jsonb; bad jsonb;
begin
  if has_function_privilege('anon','public.publish_direct_movement_program(uuid,jsonb,jsonb,jsonb)','execute')
    or has_function_privilege('authenticated','public.publish_direct_movement_program(uuid,jsonb,jsonb,jsonb)','execute')
    or not has_function_privilege('service_role','public.publish_direct_movement_program(uuid,jsonb,jsonb,jsonb)','execute')
    then raise exception 'TEST: grants';end if;
  insert into public.composers(name)values('Fixture Composer') returning id into composer;
  insert into public.works(slug,composer_id,title,catalogue)values(kid,composer,'Symphony No. 4 in F minor','Op. 36') returning id into work;
  insert into public.performances(id,kopis_performance_id,starts_at,starts_on,ends_on,title,intro_image_urls)values(pid,kid,now(),day,day,kid,array[url]);
  d:=jsonb_build_object('mt20id',kid,'prfnm',kid,'prfpdfrom','2026.10.22','prfpdto','2026.10.22','fcltynm','Fixture Hall (Fixture Hall)',
    'dtguidance','목요일(19:30)','styurls',jsonb_build_object('styurl',url));
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('kopis','performance_detail',kid,d);
  cite:=jsonb_build_object('context','program','scope','full_work','composer','[{"line_id":"L000002","quote":"Fixture Composer"}]'::jsonb,
    'title','[{"line_id":"L000003","quote":"Symphony No.4"}]'::jsonb,'catalogue','[{"line_id":"L000003","quote":"Op.36"}]'::jsonb,
    'key','[{"line_id":"L000003","quote":"f minor"}]'::jsonb,'movements','[[{"line_id":"L000004","quote":"I. Andante"}],[{"line_id":"L000005","quote":"II. Andantino"}]]'::jsonb);
  reading:=jsonb_build_object('status','text_extracted','coverage','complete','extraction_status','items_extracted','source_sha256',orig,'items',jsonb_build_array(cite),
    'lines',(select jsonb_agg(jsonb_build_object('text',l,'page_index',0) order by n) from unnest(array[stamp,'PROGRAM','Fixture Composer','Symphony No.4 in f minor Op.36','I. Andante','II. Andantino']) with ordinality x(l,n)));
  entry:=jsonb_build_object('context','program','source_index',0,'scope','unknown','model_scope','full_work','identity_reason','composer_and_catalogue',
    'reason','scope_requires_review','scoped_work_id',work,'suggested_work_id',null,'candidate_ids',jsonb_build_array(work),'evidence',cite,
    'fields',jsonb_build_object('title','Symphony No.4','composer','Fixture Composer','key','f minor','catalogue','Op.36','movements','["I. Andante","II. Andantino"]'::jsonb));
  src:=jsonb_build_object('source_url',url,'bucket','classic-hubble-sources','sha256',orig,'object_key','originals/sha256/aa/'||orig,
    'content_type','image/jpeg','performance_ids',jsonb_build_array(pid));
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('r2','source_archive',encode(sha256(convert_to(url,'UTF8')),'hex'),src);
  envelope:=jsonb_build_object('bucket',src->'bucket','source_object_key',src->'object_key','source_sha256',orig,'method','chat_model_direct_image_reading',
    'pipeline_version','codex-direct-vision-v1','reading_sha256',repeat('b',64),'reading',reading,
    'matching',jsonb_build_object('warnings','[]'::jsonb,'source_warnings','[]'::jsonb,'rejected_items','[]'::jsonb,'validation_status','complete','items',jsonb_build_array(entry)));
  raw:=envelope::text;digest_raw:=encode(sha256(convert_to(raw,'UTF8')),'hex');
  ptr:=(envelope-'reading'-'matching')||jsonb_build_object('coverage','complete','status','text_extracted','result_sha256',digest_raw,
    'result_object_key','extractions/sha256/'||left(digest_raw,2)||'/'||digest_raw);
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('codex_vision','direct_reading',kid,ptr);
  docs:=jsonb_build_object('url',url,'sha',orig,'reading_key',kid,'envelope_utf8',raw,'live_sha',orig,'content_type','image/jpeg','checked_at',now());
  candidate:=jsonb_build_array(jsonb_build_object('index',0,'work_id',work,'scope','unknown'));
  ready:=public.publish_direct_movement_program(pid,docs,candidate,null);expected:=ready->'program';
  if ready->>'status' is distinct from 'ready' or expected#>>'{0,work_id}' is distinct from work::text
    or expected#>>'{0,performed_scope}' is distinct from 'unknown' or expected#>'{0,scope_details}' is distinct from '["I. Andante","II. Andantino"]'::jsonb
    then raise exception 'TEST: valid programme preview %',ready;end if;
  if exists(select from public.program_items where performance_id=pid)
    or public.publish_direct_movement_program(pid,docs,jsonb_set(candidate,'{0,scope}','"full_work"'),expected)->>'status'='published'
    or public.publish_direct_movement_program(pid,jsonb_set(docs,'{envelope_utf8}','"{}"'),candidate,expected)->>'status'='published'
    or public.publish_direct_movement_program(pid,jsonb_set(docs,'{live_sha}','"x"'),candidate,expected)->>'status'='published'
    or public.publish_direct_movement_program(pid,docs,candidate,jsonb_set(expected,'{0,scope_details}','[]'))->>'status'='published'
    then raise exception 'TEST: caller altered trusted evidence';end if;
  foreach bad in array array[
    jsonb_set(reading,'{lines,0,text}',to_jsonb(replace(stamp,'TUR','FRI'))),
    jsonb_set(reading,'{lines,0,text}',to_jsonb(replace(stamp,'7:30','8:30'))),
    jsonb_set(reading,'{lines,0,text}',to_jsonb(replace(stamp,'Fixture Hall','Another Hall'))),
    jsonb_set(reading,'{lines,1,text}','"PROFILE"'),
    jsonb_set(reading,'{lines}',reading->'lines'||'[{"page_index":0,"text":"10/23 other concert"}]'::jsonb),
    jsonb_set(reading,'{lines,5,text}','"II. Presto"')
  ] loop
    if public.direct_movement_program_section(bad,d,day) is not null then
      if bad#>>'{lines,5,text}'='II. Presto' then
        if public.direct_movement_citations(bad,cite,1) is not null then raise exception 'TEST: untethered movement';end if;
      else raise exception 'TEST: ambiguous date, venue or section';end if;
    end if;
  end loop;
  bad:=jsonb_set(reading,'{lines,3,text}','"Symphony No.4 in f minor Op.360"');
  if public.direct_movement_citations(bad,cite,1) is not null then raise exception 'TEST: Op.36 cannot be clipped from Op.360';end if;
  bad:=jsonb_set(reading,'{items}',reading->'items'||jsonb_build_array(jsonb_build_object('context','program','title','[{"line_id":"L000004","quote":"Another work"}]'::jsonb)));
  if public.direct_movement_citations(bad,cite,1) is not null then raise exception 'TEST: movement crosses into another work';end if;
  update public.works set catalogue='Op. 48' where id=work;
  if public.publish_direct_movement_program(pid,docs,candidate,expected)->>'status'='published' then raise exception 'TEST: stale catalogue';end if;
  update public.works set catalogue='Op. 36' where id=work;
  update public.composers set name='Unrelated Composer' where id=composer;
  if public.publish_direct_movement_program(pid,docs,candidate,expected)->>'status'='published' then raise exception 'TEST: changed composer';end if;
  update public.composers set name='Fixture Composer' where id=composer;
  if not public.direct_printed_composer('P. I. Tchaikovsky','Pyotr Ilyich Tchaikovsky',null)
    or public.direct_printed_composer('F. I. Tchaikovsky','Pyotr Ilyich Tchaikovsky',null)
    or public.direct_printed_composer('Tchaikovsky','Pyotr Ilyich Tchaikovsky',null) then raise exception 'TEST: composer initials';end if;
  insert into public.program_items(performance_id,display_title,source_provider,source_type,confidence,position)values(pid,'Protected','nol','official',0,0);
  if public.publish_direct_movement_program(pid,docs,candidate,expected)->>'status' is distinct from 'existing_program_preserved' then raise exception 'TEST: NOL preserved';end if;
  delete from public.program_items where performance_id=pid;
  update public.performances set program_status='selected_on_day' where id=pid;
  if public.publish_direct_movement_program(pid,docs,candidate,null)->>'status' is distinct from 'existing_program_preserved'
    then raise exception 'TEST: selected-on-day status lost';end if;
  update public.performances set program_status='unknown' where id=pid;
  result:=public.publish_direct_movement_program(pid,docs,candidate,expected);
  if result->>'status' is distinct from 'published' or (select program_status from public.performances where id=pid) is distinct from 'partially_confirmed'
    then raise exception 'TEST: no scoped publication %',result;end if;
  select id into strict saved_id from public.program_items where performance_id=pid;
  if public.publish_direct_vision_program(pid,'{}','{}','{}','{}','[]')->>'status' is distinct from 'existing_program_preserved'
    then raise exception 'TEST: legacy single-source writer must not erase exact movements';end if;
  if public.publish_direct_movement_program(pid,docs,candidate,null)->>'status' is distinct from 'unchanged'
    or (select id from public.program_items where performance_id=pid) is distinct from saved_id
    or not exists(select from public.provider_records where entity_type='movement_program_publication' and payload->'after'=expected)
    then raise exception 'TEST: scope/history/replay';end if;
end $test$;
rollback;
select 'PASS: dated direct programme; identified catalogue, original movements and immutable publication' as result;
