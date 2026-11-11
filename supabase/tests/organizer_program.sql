begin;
do $test$
declare p uuid:=gen_random_uuid(); right_id uuid:=gen_random_uuid(); wrong_id uuid:=gen_random_uuid(); w uuid; b uuid; r jsonb; proof jsonb; changed jsonb; ref jsonb; result jsonb;
begin
  if has_function_privilege('anon','public.publish_organizer_program(uuid,jsonb,jsonb)','execute') or
     has_function_privilege('authenticated','public.organizer_program_items(jsonb,jsonb)','execute') then raise exception 'public write privilege';end if;
  insert into public.composers(id,name) values(right_id,'Morten Lauridsen'),(wrong_id,'Samuel Barber');
  insert into public.works(slug,title,composer_id)values('organizer-lauridsen','Sure on This Shining Night',right_id) returning id into w;
  insert into public.works(slug,title,composer_id)values('organizer-barber','Sure on This Shining Night',wrong_id) returning id into b;
  ref:='{"context":"program","scope":"full_work","key":null,"catalogue":null,"title":[{"line_id":"L000001","quote":"Sure on this shining night"}],"composer":[{"line_id":"L000001","quote":"Morten Lauridsen"}],"movements":[]}';
  r:=jsonb_build_object('status','text_extracted','coverage','complete','extraction_status','items_extracted','items',jsonb_build_array(ref),
   'lines','[{"page_index":0,"text":"PROGRAM"},{"page_index":0,"text":"Sure on this shining night Morten Lauridsen"}]'::jsonb);
  proof:=jsonb_build_object('format','national_theatre','event','{"program":["Sure on this shining night 별빛 가득한 이밤에 ❘ Morten Lauridsen"]}'::jsonb,
   'rows',jsonb_build_array(jsonb_build_object('index',0,'work_id',w,'slug','organizer-lauridsen','canonical_title','Sure on This Shining Night',
    'composer_id',right_id,'canonical_credit','Morten Lauridsen','official_title','Sure on this shining night 별빛 가득한 이밤에','official_credit','Morten Lauridsen',
    'poster_title','Sure on this shining night','poster_credit','Morten Lauridsen','line',0)));
  result:=public.organizer_program_items(r,proof);
  if result#>>'{0,work_id}' is distinct from w::text or result#>>'{0,performed_scope}' is distinct from 'unknown' then raise exception 'correct composer lost';end if;
  foreach changed in array array[
    jsonb_set(proof,'{rows,0,work_id}',to_jsonb(b)),jsonb_set(proof,'{rows,0,canonical_credit}','"Samuel Barber"'),
    jsonb_set(proof,'{rows,0,line}','-1'),jsonb_set(proof,'{rows,0,poster_title}','"Sure"'),
    jsonb_set(proof,'{event,program,0}','"Sure on this shining night ❘ Samuel Barber"'),
    jsonb_set(proof,'{rows}',(proof->'rows')||(proof->'rows'))
  ] loop
    if public.organizer_program_items(r,changed) is not null then raise exception 'accepted unrelated identity';end if;
  end loop;
  if public.organizer_program_items(jsonb_set(r,'{items,0,context}','"biography"'),proof) is not null
      or public.organizer_program_items(jsonb_set(r,'{items,0,scope}','"arrangement"'),proof) is not null
      or public.organizer_program_items(jsonb_set(r,'{lines,1,text}','"different line"'),proof) is not null
    then raise exception 'unverified scope or review';end if;
end $test$;
rollback;
select 'PASS: private organizer publication; exact credits and scope, homonyms stay separate' as result;
