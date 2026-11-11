begin;
do $$
declare
  pid uuid:=gen_random_uuid(); kid text:='test-'||pid; cid uuid; w1 uuid; w2 uuid;
  title text:='Sheet fixture'; artist text:='Sheet Composer'; venue text:='Fixture Hall';
  stamp text:='2026.10.22. 7:30PM'; day date:='2026-10-22';
  sty text:=E'[Program]\n\nSheet Composer <First title> for Tape (2026)\nSheet Composer <Second title 3.5> for Piano (2025/26, revised P.)';
  urls text[]; raw text; src jsonb; ptr jsonb; obs jsonb; docs jsonb:='[]'; result jsonb; items jsonb;
  orig text; sha text; docid text; i integer; lines text[]; ref jsonb; refs jsonb; pos integer; name text; old_ids uuid[];
  wrong jsonb; wrong_raw text; old_ptr jsonb; altered jsonb;
begin
  if has_function_privilege('anon','public.publish_direct_kopis_sheets(uuid,text,jsonb,jsonb)','execute')
     or has_function_privilege('authenticated','public.publish_direct_kopis_sheets(uuid,text,jsonb,jsonb)','execute') then raise exception 'TEST: public writer';end if;
  insert into public.composers(name) values(artist) returning id into cid;
  insert into public.works(composer_id,slug,title) values(cid,kid||'-1','First title') returning id into w1;
  insert into public.works(composer_id,slug,title) values(cid,kid||'-2','Second title #3.5') returning id into w2;
  insert into public.work_aliases(work_id,alias,source) values(w2,'Second title 3.5','verified:https://example.invalid/edition');
  for i in 0..2 loop
    urls:=array_append(urls,'https://www.kopis.or.kr/upload/'||kid||'-'||i||'.jpg');
    orig:=encode(sha256(convert_to(urls[i+1],'utf8')),'hex');
    src:=jsonb_build_object('bucket','classic-hubble-sources','source_url',urls[i+1],'sha256',orig,'content_type','image/jpeg',
      'object_key','originals/sha256/'||left(orig,2)||'/'||orig,'performance_ids',jsonb_build_array(pid));
    insert into public.provider_records(provider,entity_type,provider_id,payload) values('r2','source_archive',orig,src);
    if i=0 then lines:=array[title,stamp,venue];refs:='[]';
    else
      name:=case i when 1 then 'first title' else 'second title #3.5' end;
      lines:=case i when 1 then array['<'||title||'> '||stamp||' '||venue,artist,name||' (2026)','for Tape']
        else array[artist,name||' (2025/26)','for Piano'] end;pos:=case i when 1 then 1 else 0 end;
      ref:=jsonb_build_object('context','program','scope','unknown','key',null,'catalogue',null,'movements','[]'::jsonb,
        'composer',jsonb_build_array(jsonb_build_object('line_id','L'||lpad(pos::text,6,'0'),'quote',artist)),
        'title',jsonb_build_array(jsonb_build_object('line_id','L'||lpad((pos+1)::text,6,'0'),'quote',name)));refs:=jsonb_build_array(ref);
    end if;
    obs:=jsonb_build_object('source_sha256',orig,'coverage','complete','status','text_extracted','items',refs,
      'extraction_status',case when i=0 then 'no_program_identified' else 'items_extracted' end,
      'lines',(select jsonb_agg(jsonb_build_object('page_index',0,'text',t) order by n) from unnest(lines) with ordinality v(t,n)));
    raw:=obs::text;sha:=encode(sha256(convert_to(raw,'utf8')),'hex');docid:=encode(sha256(convert_to(kid||i::text,'utf8')),'hex');
    ptr:=jsonb_build_object('source_sha256',orig,'source_object_key',src->>'object_key','bucket','classic-hubble-sources',
      'reading_sha256',sha,'pipeline_version','codex-direct-vision-v1','method','chat_model_direct_image_reading',
      'status','text_extracted','coverage','complete','result_sha256',sha,'result_object_key','extractions/sha256/'||left(sha,2)||'/'||sha);
    insert into public.provider_records(provider,entity_type,provider_id,payload) values('codex_vision','direct_reading',docid,ptr);
    docs:=docs||jsonb_build_array(jsonb_build_object('url',urls[i+1],'sha',orig,'reading_key',docid,'reading_utf8',raw,
      'live_sha',orig,'content_type','image/jpeg','checked_at',now()));
  end loop;
  insert into public.performances(id,title,kopis_performance_id,starts_at,starts_on,ends_on,intro_image_urls,synopsis)
    values(pid,title,kid,now(),day,day,urls,sty);
  insert into public.provider_records(provider,entity_type,provider_id,payload) values('kopis','performance_detail',kid,
    jsonb_build_object('mt20id',kid,'prfnm',title,'prfpdfrom','2026.10.22','prfpdto','2026.10.22','fcltynm',venue,
      'styurls',jsonb_build_object('styurl',urls),'sty',sty));
  sha:=encode(sha256(convert_to(sty,'utf8')),'hex');
  result:=public.publish_direct_kopis_sheets(pid,sha,docs,null);items:=result->'program';
  if result->>'status' is distinct from 'ready' or items#>>'{0,work_id}' is distinct from w1::text
     or items#>>'{1,work_id}' is distinct from w2::text or items#>>'{1,display_title}' is distinct from 'second title #3.5'
     or items#>>'{1,performed_scope}' is distinct from 'unknown' or exists(select from public.program_items where performance_id=pid)
     then raise exception 'TEST: invalid preview %',result; end if;
  if public.publish_direct_kopis_sheets(pid,repeat('0',64),docs,items)->>'status'='published'
     or public.publish_direct_kopis_sheets(pid,sha,docs-0,items)->>'status'='published'
     or public.publish_direct_kopis_sheets(pid,sha,jsonb_set(docs,'{1,reading_utf8}','"{}"'),items)->>'status'='published'
     or public.publish_direct_kopis_sheets(pid,sha,jsonb_set(docs,'{2,live_sha}','"wrong"'),items)->>'status'='published'
     or public.publish_direct_kopis_sheets(pid,sha,jsonb_set(docs,'{2,checked_at}',to_jsonb(now()-interval '1 hour')),items)->>'status'='published'
     or public.publish_direct_kopis_sheets(pid,sha,docs,jsonb_set(items,'{0,work_id}',to_jsonb(w2)))->>'status'='published'
     then raise exception 'TEST: stale/caller-forged evidence written';end if;
  select payload into old_ptr from public.provider_records where provider='codex_vision' and entity_type='direct_reading' and provider_id=docid;
  obs:=(docs#>>'{2,reading_utf8}')::jsonb;
  foreach wrong in array array[
    jsonb_set(obs,'{lines}',obs->'lines'||'[{"page_index":0,"text":"2026.10.23. 7:30PM"}]'::jsonb),
    jsonb_set(obs,'{lines}',obs->'lines'||'[{"page_index":0,"text":"10/23"}]'::jsonb),
    jsonb_set(obs,'{lines}',obs->'lines'||'[{"page_index":0,"text":"23 October"}]'::jsonb),
    jsonb_set(obs,'{lines}',obs->'lines'||'[{"page_index":0,"text":"10.23 19:30"}]'::jsonb),
    jsonb_set(obs,'{lines}',obs->'lines'||'[{"page_index":0,"text":"Performer biography"}]'::jsonb),
    jsonb_set(obs,'{lines,2,text}','"for Violin"'),jsonb_set(obs,'{items,0,composer,0,line_id}','"L000001"'),
    jsonb_set(obs,'{items,0,title,0,quote}','"second title"'), jsonb_set(obs,'{items,0,scope}','"full_work"'),
    jsonb_set(obs,'{lines,1,text}','"second title #3.5 (2024)"')
  ] loop
    wrong_raw:=wrong::text;altered:=jsonb_set(docs,'{2,reading_utf8}',to_jsonb(wrong_raw));
    update public.provider_records set payload=jsonb_set(old_ptr,'{reading_sha256}',
      to_jsonb(encode(sha256(convert_to(wrong_raw,'utf8')),'hex')))
      where provider='codex_vision' and entity_type='direct_reading' and provider_id=docid;
    if public.publish_direct_kopis_sheets(pid,sha,altered,items)->>'status'='published' then raise exception 'TEST: genuine but incompatible reading';end if;
  end loop;
  update public.provider_records set payload=old_ptr where provider='codex_vision' and entity_type='direct_reading' and provider_id=docid;
  insert into public.work_aliases(work_id,alias,source) values(w1,'External spelling','wikidata:Qfixture');
  if public.publish_direct_kopis_sheets(pid,sha,docs,null)->>'status' is distinct from 'edition_or_identity_unverified'
    then raise exception 'TEST: uncurated imported work';end if;
  delete from public.work_aliases where work_id=w1;
  insert into public.works(composer_id,slug,title) values(cid,'wikidata-'||kid,'First title');
  if public.publish_direct_kopis_sheets(pid,sha,docs,null)->>'status' is distinct from 'edition_or_identity_unverified'
    then raise exception 'TEST: duplicate work identity';end if;
  delete from public.works where slug='wikidata-'||kid;
  delete from public.work_aliases where work_id=w2;
  if public.publish_direct_kopis_sheets(pid,sha,docs,items)->>'status'='published' then raise exception 'TEST: lost edition hash sign';end if;
  insert into public.work_aliases(work_id,alias,source) values(w2,'Second title 3.5','verified:https://example.invalid/edition');
  insert into public.program_items(performance_id,position,source_provider,display_title,source_type,confidence) values(pid,0,'nol','Protected','official',0);
  if public.publish_direct_kopis_sheets(pid,sha,docs,items)->>'status' is distinct from 'existing_program_preserved'
    or public.publish_direct_kopis_sheets(pid,sha,docs,null)->>'status' is distinct from 'existing_program_preserved' then raise exception 'TEST: protected programme';end if;
  delete from public.program_items where performance_id=pid and source_provider='nol';
  result:=public.publish_direct_kopis_sheets(pid,sha,docs,items);
  if result is distinct from '{"status":"published","items":2}'::jsonb then raise exception 'TEST: no publication %',result;end if;
  select array_agg(id order by position) into old_ids from public.program_items where performance_id=pid;
  result:=public.publish_direct_kopis_sheets(pid,sha,docs,items);
  if result->>'status' is distinct from 'unchanged' or old_ids is distinct from
    (select array_agg(id order by position) from public.program_items where performance_id=pid)
    or not exists(select from public.provider_records where entity_type='sheet_bundle_publication' and payload->'after'=items)
    then raise exception 'TEST: replay or audit';end if;
end;
$$;
rollback;
select 'PASS: independently bound multi-sheet programme, exact editions, protected rows, history and idempotence' as result;
