begin;
do $test$
declare
  sty text:=E'[PROGRAM]\nSop. 주수연 · Kl. 이고은\nDas Mädchen, D 652\n\n— Pause —\nTen. 조창후 · Kl. 이고은\nDie Nebensonnen, D 911 No. 23';
  songs jsonb; r jsonb; d jsonb; bad text; credit text:='슈베르트 가곡 속에서 비춰진 소녀들의 모습을 모아놓은 작품들';
begin
  songs:=public.kopis_typed_lieder_lines(sty);
  if songs is distinct from '[{"position":0,"line":2,"title":"Das Mädchen","literal":"Das Mädchen, D 652","number":"652","member":null},
     {"position":1,"line":6,"title":"Die Nebensonnen","literal":"Die Nebensonnen, D 911 No. 23","number":"911","member":"23"}]'::jsonb then raise exception 'TEST: wrong projected rows %',songs;end if;
  foreach bad in array array[replace(sty,'[PROGRAM]','[프로필]'),sty||E'\n2026.10.21',replace(sty,'D 652','D 652b'),
    replace(sty,'D 652','D 652 (arr.)'),replace(sty,'No. 23','No. 23-24'),replace(sty,E'Sop. 주수연 · Kl. 이고은\n',''),
    replace(sty,'— Pause —',E'— Pause —\n— Pause —'),replace(sty,'Das Mädchen','2026-10-22'),sty||E'\nSop. 주수연 · Kl. 이고은'] loop
    if public.kopis_typed_lieder_lines(bad) is not null then raise exception 'TEST: stale section %',bad;end if;
  end loop;
  d:='{"prfnm":"제80회 한국슈베르트협회 정기연주회: 슈베르트의 노래 속 소녀","fcltynm":"예술의전당 [서울] (리사이틀홀)","dtguidance":"목요일(19:30)","prfpdfrom":"2026.10.22","prfpdto":"2026.10.22"}';
  r:=jsonb_build_object('coverage','complete','status','text_extracted','extraction_status','no_program_identified','items','[]'::jsonb,
    'lines',(select jsonb_agg(jsonb_build_object('page_index',0,'text',v) order by n) from unnest(array['한국슈베르트협회 80회 정기연주회',credit,'슈베르트의 노래 속 소녀','2026. 10. 22. THU 7:30 PM','예술의전당 리사이틀홀']) with ordinality s(v,n)));
  if public.kopis_lieder_cover(r,d,'2026-10-22') is not true then raise exception 'TEST: valid corroboration';end if;
  if public.kopis_lieder_cover(jsonb_set(r,'{lines,1,text}','"한국슈베르트협회"'),d,'2026-10-22')
    or public.kopis_lieder_cover(jsonb_set(r,'{lines,3,text}','"2026. 10. 22. WED 7:30 PM"'),d,'2026-10-22')
    or public.kopis_lieder_cover(jsonb_set(r,'{lines,3,text}','"예매 2026. 10. 22. THU 7:30 PM"'),d,'2026-10-22')
    or public.kopis_lieder_cover(jsonb_set(r,'{lines,4,text}','"예술의전당 콘서트홀"'),d,'2026-10-22')
    or public.kopis_lieder_cover(jsonb_set(r,'{lines,2,text}','"다른 공연"'),d,'2026-10-22')
    or public.kopis_lieder_cover(jsonb_set(r,'{extraction_status}','"items_extracted"'),d,'2026-10-22')
    or public.kopis_lieder_cover(jsonb_set(r,'{lines}',r->'lines'||'[{"page_index":0,"text":"10월 21일"}]'),d,'2026-10-22')
    or public.kopis_lieder_cover(r,jsonb_set(d,'{prfpdto}','"2026.10.23"'),'2026-10-22') then raise exception 'TEST: false date, composer or title';end if;
  if has_function_privilege('anon','public.publish_kopis_typed_recital(uuid,jsonb,jsonb,jsonb)','execute')
    or has_function_privilege('authenticated','public.publish_kopis_typed_recital(uuid,jsonb,jsonb,jsonb)','execute') then raise exception 'TEST: publicly callable';end if;
end $test$;

do $publish$
declare
  pid uuid:=gen_random_uuid(); wid uuid:=gen_random_uuid(); cid uuid:=gen_random_uuid(); kid text:='PF999991';
  url text:='https://example.test/recital.jpg'; sha text:=repeat('b',64); rs text:=repeat('a',64); r jsonb; detail jsonb; doc jsonb;
  raw text; rd text; proof text; k text; rec jsonb; candidate jsonb; items jsonb; s jsonb; sty text:=E'[PROGRAM]\nSop. 주수연 · Kl. 이고은\nDas Mädchen, D 652\nDie Nebensonnen, D 911 No. 23';
begin
  insert into public.composers(id,name) values(cid,'Franz Schubert');
  insert into public.works(id,slug,title,composer_id,catalogue) values(wid,'fixture-lied-'||wid,'Das Mädchen, D 652',cid,'D. 652');
  detail:=jsonb_build_object('mt20id',kid,'prfnm','제80회 한국슈베르트협회 정기연주회: 슈베르트의 노래 속 소녀','prfpdfrom','2026.10.22',
    'prfpdto','2026.10.22','dtguidance','목요일(19:30)','fcltynm','예술의전당 [서울] (리사이틀홀)','styurls',jsonb_build_object('styurl',url));
  insert into public.performances(id,title,starts_at,starts_on,ends_on,intro_image_urls,kopis_performance_id,synopsis)
    values(pid,detail->>'prfnm','2026-10-22 19:30+09','2026-10-22','2026-10-22',array[url],kid,sty);
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('kopis','performance_detail',kid,detail||jsonb_build_object('sty',sty));
  r:=jsonb_build_object('coverage','complete','status','text_extracted','extraction_status','no_program_identified','items','[]'::jsonb,'source_sha256',sha,
    'lines',(select jsonb_agg(jsonb_build_object('page_index',0,'text',v) order by n) from unnest(array['한국슈베르트협회 80회 정기연주회','Lieder von Franz Schubert',
      '슈베르트의 노래 속 소녀','2026. 10. 22. THU 7:30 PM','예술의전당 리사이틀홀']) with ordinality l(v,n)));
  rec:=jsonb_build_object('bucket','classic-hubble-sources','source_sha256',sha,'source_object_key','originals/sha256/bb/'||sha,'reading_sha256',rs,
    'pipeline_version','codex-direct-vision-v1','method','chat_model_direct_image_reading');
  raw:=(rec||jsonb_build_object('reading',r))::text;rd:=encode(sha256(convert_to(raw,'UTF8')),'hex');
  insert into public.provider_records(provider,entity_type,provider_id,payload)values
    ('r2','source_archive',encode(sha256(convert_to(url,'UTF8')),'hex'),jsonb_build_object('bucket','classic-hubble-sources','source_url',url,'object_key',rec->>'source_object_key',
      'sha256',sha,'content_type','image/jpeg','performance_ids',jsonb_build_array(pid))),
    ('codex_vision','direct_reading','test:'||rd,rec||jsonb_build_object('coverage','complete','status','text_extracted','result_sha256',rd,'result_object_key','extractions/sha256/'||left(rd,2)||'/'||rd));
  proof:=jsonb_build_object('purpose','schubert_lied_identities_v1','composer','Franz Schubert','composer_id',cid,'works',jsonb_build_array(jsonb_build_object(
    'number','652','member',null,'work_id',wid,'work_slug','fixture-lied-'||wid,'canonical_title','Das Mädchen, D 652','title_forms',jsonb_build_array('Das Mädchen'),
    'source_url','https://catalogue.test/652','reference','solo song D 652')))::text;
  k:=encode(sha256(convert_to(proof,'UTF8')),'hex');
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('catalogue_repair','lied_catalogue_authority',k,
    jsonb_build_object('bucket','classic-hubble-sources','result_sha256',k,'result_object_key','extractions/sha256/'||left(k,2)||'/'||k,'proof_utf8',proof));
  doc:=jsonb_build_object('envelope_utf8',raw,'url',url,'sha',sha,'reading_key','test:'||rd,'authority_key',k,'sty_sha',encode(sha256(convert_to(sty,'UTF8')),'hex'));
  candidate:=jsonb_build_array(jsonb_build_object('position',0,'line',2,'work_id',wid));
  s:=public.publish_kopis_typed_recital(pid,doc,candidate,null);
  if s->>'status' is distinct from 'ready' or s#>>'{program,0,display_title}' is distinct from 'Das Mädchen, D 652' then raise exception 'TEST: preview %',s;end if;
  items:=s->'program';
  if public.publish_kopis_typed_recital(pid,doc,candidate,items)->>'status' is distinct from 'live_source_check_required'
    or public.publish_kopis_typed_recital(pid,doc,jsonb_set(candidate,'{0,line}','3'),null)->>'status' is distinct from 'unsupported_member_or_line'
    or public.publish_kopis_typed_recital(pid,doc,jsonb_set(candidate,'{0,work_id}',to_jsonb(gen_random_uuid())),null)->>'status' is distinct from 'ambiguous_catalogue_authority'
    then raise exception 'TEST: tampering accepted';end if;
  doc:=doc||jsonb_build_object('live_sha',sha,'checked_at',now(),'live_detail',detail,'live_sty_sha',doc->>'sty_sha','content_type','image/jpeg');
  if public.publish_kopis_typed_recital(pid,doc,candidate,'[]')->>'status' is distinct from 'stale_preview' then raise exception 'TEST: stale preview';end if;
  insert into public.program_items(performance_id,work_id,position,source_provider,display_title)values(pid,wid,0,'nol','Earlier');
  if public.publish_kopis_typed_recital(pid,doc,candidate,items)->>'status' is distinct from 'existing_program_preserved' then raise exception 'TEST: NOL was not protected';end if;
  delete from public.program_items where performance_id=pid and source_provider='nol';
  s:=public.publish_kopis_typed_recital(pid,doc,candidate,items);
  if s->>'status' is distinct from 'published' then raise exception 'TEST: write %',s;end if;
  s:=public.publish_kopis_typed_recital(pid,doc,candidate,null);
  if s->>'status' is distinct from 'unchanged'
    or not exists(select from public.program_items where performance_id=pid and source_type::text='official' and source_provider='kopis' and performed_scope='unknown')
    or not exists(select from public.provider_records where entity_type='typed_recital_publication' and payload->>'performance_id'=pid::text and payload->'after'=items and payload->>'total_songs'='2')
    then raise exception 'TEST: publication provenance or idempotence';end if;
end $publish$;
rollback;
select 'PASS: literal recital rows and independent cover/date/venue evidence' as result;
