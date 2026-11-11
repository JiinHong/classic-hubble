begin;
create function pg_temp.fixture(lines text[]) returns jsonb language sql as $$
  select jsonb_build_object('status','text_extracted','coordinate_space','exif_oriented_pixels',
    'width',100,'height',2000,'lines',jsonb_agg(jsonb_build_object(
      'text',t,'score',0.99,'bbox',jsonb_build_array(20,n*20,80,n*20+10)) order by n))
  from unnest(lines) with ordinality v(t,n)
$$;
create function pg_temp.section(d jsonb, target date, entries jsonb default '[]') returns jsonb
language sql as $$
  select public.paddle_dated_program_section(d::text,encode(sha256(convert_to(d::text,'UTF8')),'hex'),target,entries)
$$;
do $$
declare
  d jsonb := pg_temp.fixture(array['2026. 10. 21 [수]','Program','10월 21일(수)','Composer',
    'Work','I. Moderato','10월22일(목)','Composer','Work','I. Moderato','Artist','©Presenter','Composer']);
  r jsonb := '{"composer":[{"line_id":"L000007","quote":"Composer"}],"title":[{"line_id":"L000008","quote":"Work"}],"catalogue":null,"key":null,"movements":[[{"line_id":"L000009","quote":"I. Moderato"}]]}';
  entry jsonb; wrong jsonb; bad jsonb; a jsonb; b jsonb; path text[];
begin
  if has_function_privilege('anon','public.paddle_dated_program_section(text,text,date,jsonb)','execute')
    or has_function_privilege('authenticated','public.paddle_dated_program_section(text,text,date,jsonb)','execute')
  then raise exception 'TEST: unprivileged date proof'; end if;
  entry := jsonb_build_array(jsonb_build_object('publication_eligible',true,'evidence',r,
    'fields','{"composer":"Composer","title":"Work","catalogue":null,"key":null,"movements":["I. Moderato"]}'::jsonb));
  a := pg_temp.section(d,'2026-10-21');
  b := pg_temp.section(d,'2026-10-22',entry);
  if a->>'heading_line' is distinct from '2' or a->>'end_line' is distinct from '6'
    or b is distinct from '{"version":"dated-program-section-v1","performance_date":"2026-10-22","program_line":1,"anchor_line":0,"heading_line":6,"end_line":10}'::jsonb
  then raise exception 'TEST: adjacent sets not separated: %, %',a,b; end if;
  if pg_temp.section(d,'2026-10-21',entry) is not null
    or pg_temp.section(d,'2026-10-23') is not null
    or public.paddle_dated_program_section(d::text,repeat('a',64),'2026-10-22','[]') is not null
  then raise exception 'TEST: swapped target/hash accepted'; end if;
  foreach path slice 1 in array array[
    ['0','evidence','composer','0','line_id'],['0','evidence','title','0','line_id']
  ] loop
    wrong := jsonb_set(entry,path,to_jsonb(case when path[3]='title' then 'L000004' else 'L000003' end));
    if pg_temp.section(d,'2026-10-22',wrong) is not null then raise exception 'TEST: cross-date field'; end if;
  end loop;
  foreach wrong in array array[
    jsonb_set(entry,'{0,evidence,movements,0,0,line_id}','"L000005"'),
    jsonb_set(entry,'{0,evidence,key}','[{"line_id":"L000004","quote":"Work"}]'),
    jsonb_set(entry,'{0,evidence,catalogue}','[{"line_id":"L000004","quote":"Work"}]'),
    jsonb_set(entry,'{0,evidence,composer,0,line_id}','"L000012"'),
    jsonb_set(entry,'{0,evidence,title,0,quote}','"Invented"'),
    jsonb_set(entry,'{0,fields,title}','"Another title"'),
    jsonb_set(entry,'{0,fields,movements}','["Another movement"]'),
    jsonb_set(entry,'{0,publication_eligible}','"true"')
  ] loop
    if pg_temp.section(d,'2026-10-22',wrong) is not null then raise exception 'TEST: unbound quote accepted'; end if;
  end loop;
  foreach bad in array array[
    jsonb_set(d,'{lines,0,text}','"예매 2026. 10. 21 [수]"'),
    jsonb_set(d,'{lines,0,text}','"2025. 10. 21 [수]"'),
    jsonb_set(d,'{lines,1,text}','"Ticket sales"'),
    jsonb_set(d,'{lines,2,score}','0.7'),
    jsonb_set(d,'{lines,3,text}','"예매 안내"'),
    jsonb_set(d,'{lines,4,text}','"10. 23 (금)"'),
    jsonb_set(d,'{lines,4,text}','"October 23 (Fri)"'),
    jsonb_set(d,'{lines,4,text}','"23일 (금)"'),
    jsonb_set(d,'{lines,6,text}','"10월22일(금)"'),
    jsonb_set(d,'{lines,6,text}','"10월21일(수)"'),
    jsonb_set(d,'{lines,6,text}','"11월20일(금)"'),
    jsonb_set(d,'{lines,7,page_index}','1'),
    jsonb_set(d,'{lines,8,bbox}','[1,185,15,190]'),
    jsonb_set(d,'{lines,8,bbox}','[20,60,80,70]'),
    jsonb_set(d,'{lines,8,score}','0.8999'),
    jsonb_set(d,'{lines,10,text}','"Unknown"'),
    jsonb_set(d,'{lines,12,text}','"Program"'),
    jsonb_set(jsonb_set(d,'{lines,10,text}','"Arlist"'),'{lines,11,text}','"Other"')
  ] loop
    if pg_temp.section(bad,'2026-10-22',entry) is not null then raise exception 'TEST: unsafe layout %',bad; end if;
  end loop;
  if pg_temp.section(jsonb_set(d,'{lines,10,text}','"Arlist"'),'2026-10-22',entry) is null
  then raise exception 'TEST: supported artist boundary not recognized'; end if;
end;
$$;
-- Exercise the actual locked transaction, not just its layout helper.
do $$
declare
  pid uuid := gen_random_uuid(); wid uuid := (select id from public.works limit 1);
  url text := 'https://example.invalid/dated-'||pid; target jsonb; oc jsonb; rv jsonb; src jsonb;
  raw text := pg_temp.fixture(array['2026.10.21 [수]','Program','10월21일(수)','Composer','Same work',
    '10월22일(목)','Composer','Same work Op. 18','I. Moderato','Artist'])::text;
  sha text := encode(sha256(convert_to(raw,'UTF8')),'hex');
  proof jsonb := public.paddle_dated_program_section(raw,sha,'2026-10-22','[]');
  ref jsonb := '{"context":"program","scope":"movement","composer":[{"line_id":"L000006","quote":"Composer"}],
    "title":[{"line_id":"L000007","quote":"Same work Op. 18"}],"catalogue":[{"line_id":"L000007","quote":"Op. 18"}],"key":null,
    "movements":[[{"line_id":"L000008","quote":"I. Moderato"}]]}';
  doc jsonb; ev jsonb; items jsonb; entry jsonb; result jsonb; bad jsonb; old_id uuid;
begin
  insert into public.performances(id,title,starts_at,starts_on,ends_on,intro_image_urls)
    values(pid,'Dated programme test',now(),'2026-10-22','2026-10-22',array[url]);
  target := jsonb_build_object('id',pid,'title','Dated programme test','starts_on','2026-10-22','ends_on','2026-10-22','intro_image_urls',array[url]);
  src := jsonb_build_object('source_url',url,'bucket','test','sha256',repeat('a',64),'object_key','original/'||pid,'performance_ids',jsonb_build_array(pid));
  oc := jsonb_build_object('source_sha256',src->>'sha256','bucket','test','source_object_key',src->>'object_key','pipeline_version','paddle-test',
    'status','text_extracted','processed_at',now(),'result_sha256',sha);
  rv := jsonb_build_object('review_id',pid,'version','paddle-partial-program-v1','method','reviewed_paddle_text','bucket','test',
    'source_sha256',src->>'sha256','document_sha256',sha,'response',jsonb_build_object('status','items_extracted','document_sha256',sha,'items',jsonb_build_array(ref)));
  insert into public.provider_records(provider,entity_type,provider_id,payload) values
    ('r2','source_archive',encode(sha256(convert_to(url,'UTF8')),'hex'),src),
    ('paddleocr','ocr_result',pid::text,oc),('paddle_review','program_selection',pid::text,rv);
  entry := jsonb_build_object('context','program','scope','movement','scoped_work_id',wid,'model_scope','movement','evidence',ref,
    'identity_reason','composer_and_alias','publication_eligible',true,'source_index',0,
    'fields','{"composer":"Composer","title":"Same work Op. 18","catalogue":"Op. 18","key":null,"movements":["I. Moderato"]}'::jsonb);
  doc := jsonb_build_object('source',src,'ocr',oc,'review',rv,'date_binding','dated_section','program_section',proof,
    'live_sha256',src->>'sha256','source_checked_at',now(),'matching',jsonb_build_object('document_sha256',sha,'validation_status','complete',
    'source_warnings','[]'::jsonb,'warnings','[]'::jsonb,'items',jsonb_build_array(entry)));
  ev := jsonb_build_object('publication_version','paddle-performance-bundle-v2','date_binding_version','concert-date-headings-v22',
    'performance_date','2026-10-22','section_ocr_utf8',raw);
  items := jsonb_build_array(jsonb_build_object('work_id',wid,'position',0,'display_title','Same work Op. 18','composer_name','Composer',
    'performed_scope','movement','scope_details',jsonb_build_array('I. Moderato'),'source_url',url));
  foreach bad in array array[jsonb_set(doc,'{program_section,heading_line}','2'),
    jsonb_set(doc,'{date_binding}','"target"'),doc-'program_section'] loop
    begin
      perform public.publish_paddle_program_bundle(pid,target,jsonb_build_array(bad),ev,items);
      raise exception 'TEST: forged section admitted';
    exception when raise_exception then
      if sqlerrm not in ('Invalid date section proof','Unexpected date section proof') then raise; end if;
    end;
  end loop;
  begin
    perform public.publish_paddle_program_bundle(pid,target,jsonb_build_array(doc),ev||'{"section_ocr_utf8":"{}"}',items);
    raise exception 'TEST: changed raw accepted';
  exception when raise_exception then if sqlerrm <> 'Invalid date section proof' then raise; end if; end;
  result := public.publish_paddle_program_bundle(pid,target,jsonb_build_array(doc),ev,items);
  if result->>'status' is distinct from 'published' then raise exception 'TEST: did not publish %',result; end if;
  select id into strict old_id from public.program_items where performance_id=pid and performed_scope='movement';
  if not exists(select 1 from public.provider_records where entity_type='bundle_publication' and payload->>'performance_id'=pid::text
    and payload#>'{documents,0,program_section}'=proof and not ((payload->'evaluation') ? 'section_ocr_utf8'))
  then raise exception 'TEST: incorrect persisted proof'; end if;
  result := public.publish_paddle_program_bundle(pid,target,jsonb_build_array(doc),ev,items);
  if result->>'status' is distinct from 'unchanged' or not exists(select 1 from public.program_items where id=old_id)
  then raise exception 'TEST: duplicate publication'; end if;
end;
$$;
rollback;
select 'PASS: two dated programmes, original pixel layout, OCR integrity, field and movement isolation' as result;
