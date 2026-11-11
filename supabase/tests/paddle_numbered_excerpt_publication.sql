begin;
do $$
declare
  pid uuid := gen_random_uuid(); c uuid; w uuid; url text := 'https://example.invalid/numbered-'||pid;
  raw text; sha text; proof jsonb; src jsonb; oc jsonb; rv jsonb; target jsonb; ev jsonb; doc jsonb;
  title text; parts text[]; line_no integer; i integer; ref jsonb; entry jsonb; refs jsonb := '[]'; entries jsonb := '[]';
  items jsonb := '[]'; bad jsonb; result jsonb; kept uuid[];
begin
  select id into w from public.works where slug='poulenc-quinze-improvisations';
  if w is null then
    insert into public.composers(name,name_ko) values('Francis Poulenc','프랑시스 풀랑크') returning id into c;
    insert into public.works(slug,title,composer_id) values('poulenc-quinze-improvisations','Les Quinze Improvisations',c) returning id into w;
    insert into public.work_aliases(work_id,alias,source) values(w,'15 Improvisations for piano','verified:https://catalogue.bnf.fr/ark:/12148/cb139840284');
  end if;
  select jsonb_build_object('status','text_extracted','coordinate_space','exif_oriented_pixels','width',100,'height',500,
    'lines',jsonb_agg(jsonb_build_object('text',v,'score',0.99,'bbox',jsonb_build_array(10,n*20,90,n*20+10)) order by n))::text
    into raw from unnest(array['2026.10.21 [수]','Program','10월21일(수)','프랑시스 풀랑크','즉흥곡 제7번~제12번',
      '프랑시스 풀랑크','즉흥곡 제1번~제6번,제13번~제15번','10월22일(목)','Other work','Artist']) with ordinality a(v,n);
  sha := encode(sha256(convert_to(raw,'UTF8')),'hex'); proof := public.paddle_dated_program_section(raw,sha,'2026-10-21');
  for i in 0..1 loop
    line_no := 4+2*i; title := raw::jsonb->'lines'->line_no->>'text'; parts := string_to_array(substr(title,5),',');
    ref := jsonb_build_object('context','program','scope','excerpt','key',null,'catalogue',null,
      'composer',jsonb_build_array(jsonb_build_object('line_id','L'||lpad((line_no-1)::text,6,'0'),'quote','프랑시스 풀랑크')),
      'title',jsonb_build_array(jsonb_build_object('line_id','L'||lpad(line_no::text,6,'0'),'quote',title)),
      'movements',(select jsonb_agg(jsonb_build_array(jsonb_build_object('line_id','L'||lpad(line_no::text,6,'0'),'quote',v)) order by n)
        from unnest(parts) with ordinality a(v,n)));
    refs := refs||jsonb_build_array(ref);
    entry := jsonb_build_object('context','program','scope','excerpt','model_scope','excerpt','evidence',ref,'source_index',i,
      'publication_eligible',true,'identity_reason','composer_and_numbered_excerpt','scoped_work_id',w,'suggested_work_id',null,
      'fields',jsonb_build_object('composer','프랑시스 풀랑크','title',title,'key',null,'catalogue',null,'movements',parts));
    entries := entries||jsonb_build_array(entry);
    items := items||jsonb_build_array(jsonb_build_object('work_id',w,'position',i,'display_title',title,
      'composer_name','프랑시스 풀랑크','performed_scope','excerpt','scope_details',parts,'source_url',url));
  end loop;
  insert into public.performances(id,title,starts_at,starts_on,ends_on,intro_image_urls)
    values(pid,'Numbered excerpt test',now(),'2026-10-21','2026-10-21',array[url]);
  target := jsonb_build_object('id',pid,'title','Numbered excerpt test','starts_on','2026-10-21','ends_on','2026-10-21','intro_image_urls',array[url]);
  src := jsonb_build_object('source_url',url,'bucket','test','sha256',repeat('a',64),'object_key','original/'||pid,'performance_ids',jsonb_build_array(pid));
  oc := jsonb_build_object('source_sha256',src->>'sha256','bucket','test','source_object_key',src->>'object_key','pipeline_version','paddle-test',
    'status','text_extracted','processed_at',now(),'result_sha256',sha);
  rv := jsonb_build_object('review_id',pid,'version','paddle-partial-program-v1','method','reviewed_paddle_text','bucket','test',
    'source_sha256',src->>'sha256','document_sha256',sha,'response',jsonb_build_object('status','items_extracted','document_sha256',sha,'items',refs));
  insert into public.provider_records(provider,entity_type,provider_id,payload) values
    ('r2','source_archive',encode(sha256(convert_to(url,'UTF8')),'hex'),src),('paddleocr','ocr_result',pid::text,oc),
    ('paddle_review','program_selection',pid::text,rv);
  doc := jsonb_build_object('source',src,'ocr',oc,'review',rv,'date_binding','dated_section','program_section',proof,
    'live_sha256',src->>'sha256','source_checked_at',now(),'matching',jsonb_build_object('document_sha256',sha,'validation_status','complete',
    'source_warnings','[]'::jsonb,'warnings','[]'::jsonb,'items',entries));
  ev := jsonb_build_object('publication_version','paddle-performance-bundle-v2','date_binding_version','concert-date-headings-v22',
    'performance_date','2026-10-21','section_ocr_utf8',raw);
  foreach bad in array array[jsonb_set(doc,'{matching,items,0,scoped_work_id}',to_jsonb(gen_random_uuid())),
    jsonb_set(doc,'{matching,items,0,suggested_work_id}',to_jsonb(w))] loop
    begin
      perform public.publish_paddle_program_bundle(pid,target,jsonb_build_array(bad),ev,items);
      raise exception 'TEST: forged identity'; exception when raise_exception then if sqlerrm<>'Invalid numbered excerpt' then raise; end if;
    end;
  end loop;
  begin
    perform public.publish_paddle_program_bundle(pid,target,jsonb_build_array((doc-'program_section')||'{"date_binding":"target"}'),
      ev-'section_ocr_utf8',items);
    raise exception 'TEST: unbound collection'; exception when raise_exception then
      if sqlerrm<>'Bundle item differs from reviewed evidence' then raise; end if;
  end;
  result := public.publish_paddle_program_bundle(pid,target,jsonb_build_array(doc),ev,items);
  if result<> '{"status":"published","items":2}'::jsonb then raise exception 'TEST: expected both excerpts: %',result; end if;
  select array_agg(id order by position) into kept from public.program_items where performance_id=pid;
  if cardinality(kept)<>2 then raise exception 'TEST: missing rows'; end if;
  result := public.publish_paddle_program_bundle(pid,target,jsonb_build_array(doc),ev,items);
  if result->>'status'<>'unchanged' then raise exception 'TEST: duplicate'; end if;
  result := public.publish_paddle_program_bundle(pid,target,jsonb_build_array(jsonb_set(doc,'{matching,items,1,publication_eligible}','false')),
    ev,jsonb_build_array(items->0));
  if result->>'status' is distinct from 'existing_program_preserved' or kept is distinct from
    (select array_agg(id order by position) from public.program_items where performance_id=pid)
    then raise exception 'TEST: one collection excerpt silently displaced the other: %',result; end if;
end;
$$;
rollback;
select 'PASS: date-bound parent is recomputed atomically; neither excerpt can erase the other' as result;
