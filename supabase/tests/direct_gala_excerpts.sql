begin;
do $test$
declare
  d jsonb:='{"prfnm":"오페라 축제, 그랜드 오페라 갈라쇼: Viva Verdi","prfpdfrom":"2026.10.22","prfpdto":"2026.10.22","dtguidance":"목요일(19:30)","fcltynm":"강동아트센터 (대극장 한강)"}';
  proof jsonb:='{"name":"Viva Verdi","date":"2026-10-22","event_title":"오페라 축제, 그랜드 오페라 갈라쇼: Viva Verdi","clock":"19:30","venue":"강동아트센터","hall":"대극장 한강","short_venue":"GAC","festival_heading":"2026 SEOUL OPERA FESTIVAL","printed_composer":"베르디"}';
  r jsonb; broken jsonb; day date:='2026-10-22'; auth uuid; wid uuid; alt uuid;
  cite jsonb; frozen jsonb; ctx jsonb; v jsonb;
begin
  if has_function_privilege('anon','public.direct_gala_window(jsonb,jsonb,date,jsonb)','execute')
     or has_function_privilege('authenticated','public.direct_gala_item(jsonb,jsonb,jsonb,jsonb,uuid)','execute') then raise exception 'TEST: private only';end if;
  insert into public.composers(name,name_ko)values('Giuseppe Verdi','주세페 베르디') returning id into auth;
  insert into public.works(slug,title,composer_id)values('test-rigoletto','Rigoletto',auth) returning id into wid;
  proof:=proof||'{"calendar":{"year":2026,"named_schedule_row":["그랜드 오페라 갈라쇼 <Viva Verdi>","10. 22.(목) 19:30","대극장"]},"catalogue_source":{"printed_names":["Rigoletto"]}}'::jsonb
    ||jsonb_build_object('composer','Giuseppe Verdi','composer_ko','주세페 베르디','composer_id',auth,'works',
    jsonb_build_array(jsonb_build_object('work_id',wid,'canonical','Rigoletto','printed_title','Rigoletto','slug','test-rigoletto')));
  cite:='{"context":"program","scope":"excerpt","key":null,"catalogue":null,"composer":[{"line_id":"L000003","quote":"베르디"}],"title":[{"line_id":"L000006","quote":"Rigoletto"}],"movements":[[{"line_id":"L000006","quote":"Caro nome"}]]}';
  frozen:=jsonb_build_object('context','program','scope','excerpt','model_scope','excerpt','identity_reason','no_candidate','reason','scope_requires_review',
    'candidate_ids','[]'::jsonb,'evidence',cite,'fields','{"composer":"베르디","title":"Rigoletto","movements":["Caro nome"],"catalogue":null,"key":null}'::jsonb);
  r:=jsonb_build_object('status','text_extracted','coverage','complete','extraction_status','items_extracted','items',jsonb_build_array(cite),'lines',
    (select jsonb_agg(jsonb_build_object('page_index',0,'text',t) order by i) from unnest(array[
    '그랜드오페라갈라쇼 <Viva Verdi>','10. 22.목 오후 7시 30분','GAC 대극장 한강','서울오페라페스티벌은 오직 베르디의 작품만으로 채우는 특별한 무대 <Viva Verdi>를 선보입니다.','Viva Verdi Programs','1부',
    '리골레또 Rigoletto 그리운 이름이여 Caro nome','2026 SEOUL OPERA FESTIVAL','강동아트센터 대극장 한강 10. 22. 목 19:30 그랜드오페라갈라쇼 <Viva Verdi>']) with ordinality b(t,i)));
  ctx:=public.direct_gala_window(r,d,day,proof);
  if ctx is null or public.direct_gala_item(r,cite,frozen,ctx,wid) is distinct from frozen->'fields' then raise exception 'TEST: printed gala excerpt';end if;
  foreach broken in array array[
    jsonb_set(r,'{lines,0,text}','"그랜드오페라갈라쇼 <Other>"'),
    jsonb_set(r,'{lines,1,text}','"10. 23.금 오후 7시 30분"'),
    jsonb_set(r,'{lines,1,text}','"10. 22.목 오전 7시 30분"'),
    jsonb_set(r,'{lines,2,text}','"GAC 소극장"'),
    jsonb_set(r,'{lines,3,text}','"출연 베르디 <Viva Verdi>"'),
    jsonb_set(r,'{lines,4,text}','"Other Programs"'),
    jsonb_set(r,'{lines,5,text}','"10. 23. 금 PROGRAM"'),
    jsonb_set(r,'{lines,5,text}','"예매 10.21"'),
    jsonb_set(r,'{lines,7,text}','"2025 SEOUL OPERA FESTIVAL"'),
    jsonb_set(r,'{lines,8,text}','"강동아트센터 대극장 한강 10. 23. 금 19:30 그랜드오페라갈라쇼 <Viva Verdi>"')
  ] loop
    if public.direct_gala_window(broken,d,day,proof) is not null then raise exception 'TEST: invalid event anchor %',broken;end if;
  end loop;
  if public.direct_gala_window(r,jsonb_set(d,'{dtguidance}','"금요일(19:30)"'),day,proof) is not null
    or public.direct_gala_window(r,d,day,jsonb_set(proof,'{date}','"2026-10-23"')) is not null
    or public.direct_gala_window(r,d,day,jsonb_set(proof,'{calendar,named_schedule_row,1}','"11. 22.(목) 19:30"')) is not null
    then raise exception 'TEST: official date mismatch';end if;
  foreach broken in array array[
    jsonb_set(cite,'{movements,0,0,line_id}','"L000008"'),jsonb_set(cite,'{scope}','"full_work"'),jsonb_set(cite,'{composer,0,line_id}','"L000001"')
  ] loop
    if public.direct_gala_item(r,broken,jsonb_set(frozen,'{evidence}',broken),ctx,wid) is not null then raise exception 'TEST: crossing evidence';end if;
  end loop;
  if public.direct_gala_item(jsonb_set(r,'{lines,6,text}','"리골레또 RigolettoX 그리운 이름이여 Caro nome"'),cite,frozen,ctx,wid) is not null
    or public.direct_gala_item(jsonb_set(r,'{lines,6,text}','"리골레또 Rigoletto 그리운 이름이여 NotCaro nome"'),cite,frozen,ctx,wid) is not null
    or public.direct_gala_item(r,cite,jsonb_set(frozen,'{candidate_ids}','["different"]'),ctx,wid) is not null
    or public.direct_gala_item(r,cite,frozen,jsonb_set(ctx,'{catalogue_source,printed_names}','["Rigo"]'),wid) is not null
    then raise exception 'TEST: substring or different identity';end if;
  insert into public.works(slug,title,composer_id)values('test-second-rigoletto','Rigoletto',auth) returning id into alt;
  if public.direct_gala_item(r,cite,frozen,ctx,wid) is not null then raise exception 'TEST: ambiguous parent';end if;
end $test$;
rollback;
select 'PASS: independently dated named gala, same-line printed excerpt, no version or full opera' as result;
