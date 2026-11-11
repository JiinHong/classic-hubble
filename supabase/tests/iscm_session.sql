begin;
do $test$
declare
 d date:='2026-10-21'; s text:=E'[PROGRAM]\n시간을 잇는 소리\nSounds Across Generations\n\n진규영 - 목관을 위한 <트리오>\nCHIN Kyu-Yung <Trio> for Strings';
 a jsonb; r jsonb; cid uuid:=gen_random_uuid(); wid uuid:=gen_random_uuid(); sec text[]; altered jsonb;
begin
 insert into public.composers(id,name,name_ko) values(cid,'CHIN Kyu-Yung','진규영');
 insert into public.works(id,composer_id,slug,title,title_ko) values(wid,cid,'test-iscm-trio','Trio for Strings','목관을 위한 트리오');
 sec:=array['2026 PAN Music Festival','PAN Music Festival 앙상블 - 역대 명예회장 작품전','PMF Ensemble - Works','시간을 잇는 소리','Sounds Across Generations',
 '진규영 목관을 위한 < 트리오 > (1998)','CHIN Kyu-Yung < Trio > for Strings','장소 Venue','거암아트홀','GEOAM ART HALL','일시 Date','2026년 10월 21일 (Wed) 19:30'];
 a:=jsonb_build_object('day',d,'title','제54회 범음악제, 콘서트 1. 역대 명예회장 작품전','venue','거암아트홀 (거암아트홀)','schedule','수요일(19:30)',
  'session',sec,'session_sha',encode(sha256(convert_to(array_to_string(sec,E'\n'),'utf8')),'hex'),'sources',jsonb_build_object('session',jsonb_build_object('url','https://www.iscm-korea.com/2026-PMF','sha',repeat('a',64))),
  'rows',jsonb_build_array(jsonb_build_object('work_id',wid,'slug','test-iscm-trio','composer','CHIN Kyu-Yung','credit_ko','진규영','title','Trio for Strings','title_ko','목관을 위한 트리오','year','1998')));
 r:=jsonb_build_object('status','text_extracted','coverage','complete','extraction_status','no_program_identified','items','[]'::jsonb,
  'lines',(select jsonb_agg(jsonb_build_object('page_index',0,'text',x)) from unnest(array['제54회 범음악제','2026. 10. 21 Wed.','- 10. 30 Fri.','The 54th PAN Music Festival','※ 상세 일정은 범음악제 홈페이지(QR) 참조 바랍니다.']) x));
 if public.kopis_festival_session(r,a,s,d)#>>'{0,work_id}' is distinct from wid::text then raise exception 'lost bilingual identity';end if;
 foreach altered in array array[a||'{"schedule":"목요일(19:30)"}',a||'{"venue":"다른 홀"}',a||'{"day":"2026-10-22"}',jsonb_set(a,'{rows,0,year}','"2003"'),jsonb_set(a,'{rows,0,composer}','"Yi ManBang"'),
 jsonb_set(a,'{rows,0,title}','"Trio for Winds"'),jsonb_set(a,'{sources,session,url}','"https://example.org/2026-PMF"')] loop
  if public.kopis_festival_session(r,altered,s,d) is not null then raise exception 'bad festival binding';end if;
 end loop;
 if public.kopis_festival_session(r,a,replace(s,'진규영 -','다른이 -'),d) is not null or public.kopis_festival_session(r,a,replace(s,'<트리오>','<트리오> (2003)'),d) is not null
 or public.kopis_festival_session(jsonb_set(r,'{lines,2,text}','"- 10. 30 Sat."'),a,s,d) is not null then raise exception 'conflict accepted';end if;
 if has_function_privilege('anon','public.kopis_festival_session(jsonb,jsonb,text,date)','EXECUTE') then raise exception 'unexpected public privilege';end if;
end $test$;
rollback;
select 'PASS: independently dated bilingual festival programme' as result;
