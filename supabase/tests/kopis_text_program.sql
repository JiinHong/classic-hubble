begin;
do $t$
declare
  s text:=E'[PROGRAM]\n\nG. Verdi (1813-1901)\nTriumphal March\n\nINTERMISSION\n\nThe Nutcracker 中 “Grand Pas de Deux”\n와이즈발레단 김민영, 박종희';
  r jsonb; p jsonb; c uuid:=gen_random_uuid(); w uuid:=gen_random_uuid(); other uuid:=gen_random_uuid(); m jsonb; z jsonb;
begin
  if public.kopis_text_blocks(s,'stacked') is distinct from '[["G. Verdi","Triumphal March"],null]'::jsonb
    or public.kopis_text_blocks(E'[PROGRAM]\n* Claude Debussy / Beau soir, arranged for violin and piano\n* John Adams / Road Movies','bullets') is distinct from '[null,["John Adams","Road Movies"]]'::jsonb
    or public.kopis_text_blocks(E'[PROGRAM]\n* John Adams / Road Movies\n[PROFILE]\n* John Adams / Other','bullets') is not null
    or public.kopis_text_blocks(E'[PROGRAM]\n\nJ. Haydn\nTrumpet Concerto\n\n연주자 소개\n\nJ. Williams\nOlympic Fanfare and Theme','stacked') is not null
    then raise exception 'unbound programme block';end if;
  insert into public.composers(id,name)values(c,'Giuseppe Verdi'),(other,'Samuel Barber');
  insert into public.works(id,composer_id,slug,title)values(w,c,'text-test-aida','Aida');
  r:=jsonb_build_object('position',0,'credit','G. Verdi','title','Triumphal March','work_id',w,'slug','text-test-aida','canonical_title','Aida',
    'composer','Giuseppe Verdi','composer_id',c,'source','score','work_witness','Triumphal March from the opera Aida','credit_witness','Giuseppe Verdi','scope','excerpt','detail','Triumphal March');
  p:=jsonb_build_object('style','stacked','rows',jsonb_build_array(r),'sources',jsonb_build_object('score',jsonb_build_object('sha',repeat('a',64),'url','https://example.org/score')));
  z:=public.kopis_text_program_items(s,p);
  if z#>>'{0,work_id}' is distinct from w::text or z#>>'{0,performed_scope}' is distinct from 'excerpt' or z#>'{0,scope_details}' is distinct from '["Triumphal March"]'::jsonb then raise exception 'excerpt scope lost';end if;
  foreach m in array array[jsonb_build_object('position',-1),jsonb_build_object('canonical_title','Rigoletto'),jsonb_build_object('scope','full_work'),
    jsonb_build_object('composer_id',other),jsonb_build_object('credit','F. Loewe'),jsonb_build_object('work_witness','from a different opera')] loop
    if public.kopis_text_program_items(s,jsonb_set(p,'{rows,0}',r||m)) is not null then raise exception 'unsafe link %',m;end if;
  end loop;
  insert into public.works(id,composer_id,slug,title,catalogue)values(other,c,'test-sonata','Violin Sonata No. 8 in G major','Op. 30');
  r:=r||jsonb_build_object('title','Violin Sonata No. 8 in G major, Op. 30, No. 3','work_id',other,'slug','test-sonata','scope','unknown',
    'detail',null,'canonical_title','Violin Sonata No. 8 in G major','catalogue','Op. 30','work_witness','Violin Sonata G major op. 30,3');
  s:=E'[PROGRAM]\n* Giuseppe Verdi / Violin Sonata No. 8 in G major, Op. 30, No. 3';r:=r||'{"credit":"Giuseppe Verdi"}';
  p:=jsonb_set(jsonb_set(p,'{style}','"bullets"'),'{rows,0}',r);
  if public.kopis_text_program_items(s,p) is null then raise exception 'lost complete printed group/member';end if;
  if public.kopis_text_program_items(s,jsonb_set(p,'{rows,0,work_witness}','"Violin Sonata G major op. 30,31"')) is not null then raise exception 'numeric prefix accepted';end if;
  if has_function_privilege('anon','public.publish_kopis_text_program(uuid,jsonb,jsonb)','EXECUTE') or
     has_function_privilege('authenticated','public.publish_kopis_text_program(uuid,jsonb,jsonb)','EXECUTE') then raise exception 'public can publish';end if;
end $t$;
rollback;
select 'PASS: typed KOPIS block boundaries, canonical identity, performer and excerpt controls' as result;
