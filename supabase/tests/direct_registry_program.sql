begin;
do $test$
declare
  wid uuid:=gen_random_uuid(); composer uuid:=gen_random_uuid(); slug text:='test-'||wid; target date:='2026-10-22';
  r jsonb; ref jsonb; e jsonb; proof jsonb; pointer jsonb; raw text; k text; item jsonb; another uuid;
begin
  if has_function_privilege('anon','public.direct_registry_item(jsonb,jsonb,jsonb,int,uuid,text)','execute')
    or has_function_privilege('authenticated','public.direct_registry_item(jsonb,jsonb,jsonb,int,uuid,text)','execute')
    then raise exception 'TEST: public access';end if;
  insert into public.composers(id,name) values(composer,'Fixture Composer');
  insert into public.works(id,composer_id,title,slug) values(wid,composer,'Salve Regina',slug);
  ref:='{"context":"program","scope":"full_work","composer":[{"line_id":"L000002","quote":"Fixture Composer"}],"title":[{"line_id":"L000003","quote":"Salve Regina"}],"key":null,"catalogue":null,"movements":[]}';
  r:=jsonb_build_object('items',jsonb_build_array(ref),'lines',(select jsonb_agg(jsonb_build_object('text',v,'page_index',0) order by n)
    from unnest(array['2026.10.22(목) 19:30 Fixture Hall','PROGRAM','I Fixture Composer (1935-)','Salve Regina','Another section']) with ordinality u(v,n)));
  e:=jsonb_build_object('context','program','scope','full_work','reason','composer_and_alias','identity_reason','composer_and_alias',
    'candidate_ids',jsonb_build_array(wid),'suggested_work_id',wid,'scoped_work_id',null,'evidence',ref,
    'fields',jsonb_build_object('composer','Fixture Composer','title','Salve Regina','catalogue',null,'key',null,'movements','[]'::jsonb));
  proof:=jsonb_build_object('purpose','canonical_parent_identity_v1','work_id',wid,'work_slug',slug,'canonical_title','Salve Regina',
    'composer_id',composer,'composer','Fixture Composer','catalogue',null,'tonality',null,'title_forms',jsonb_build_array('Salve Regina'),
    'source_url','https://authority.example/works/choral','edition_identified',false);
  raw:=proof::text;k:=encode(sha256(convert_to(raw,'UTF8')),'hex');pointer:=jsonb_build_object('bucket','classic-hubble-sources',
    'result_object_key','extractions/sha256/'||left(k,2)||'/'||k,'result_sha256',k,'proof_utf8',raw);
  if public.direct_registry_item(r,ref,e,1,wid,k) is not null then raise exception 'TEST: missing authority';end if;
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('catalogue_repair','parent_work_authority',k,pointer);
  item:=public.direct_registry_item(r,ref,e,1,wid,k);
  if item is distinct from e->'fields' then raise exception 'TEST: missing exact title and credit %',item;end if;
  if public.direct_registry_item(jsonb_set(r,'{lines,2,text}','"Other Composer and Fixture Composer"'),ref,e,1,wid,k) is not null
    or public.direct_registry_item(jsonb_set(r,'{lines,3,text}','"Salve Regina arrangement for piano"'),ref,e,1,wid,k) is not null
    or public.direct_registry_item(r,ref,jsonb_set(e,'{suggested_work_id}',to_jsonb(gen_random_uuid())),1,wid,k) is not null
    or public.direct_registry_item(r,ref,jsonb_set(e,'{candidate_ids}','[]'),1,wid,k) is not null
    or public.direct_registry_item(r,ref,e,3,wid,k) is not null then raise exception 'TEST: crossing section, changing identity or losing edition';end if;
  insert into public.works(composer_id,title,slug) values(composer,'Another work',slug||'-2') returning id into another;
  insert into public.work_aliases(work_id,alias,source)values(another,'Salve Regina','wikidata:test');
  if public.direct_registry_item(r,ref,e,1,wid,k) is not null then raise exception 'TEST: ambiguous alias';end if;
  delete from public.work_aliases where work_id=another;
  update public.provider_records set payload=jsonb_set(payload,'{proof_utf8}',to_jsonb(raw||' ')) where provider_id=k;
  if public.direct_registry_item(r,ref,e,1,wid,k) is not null then raise exception 'TEST: content drift';end if;
  update public.works set title='Requiem in D minor',catalogue='K. 626' where id=wid;
  insert into public.work_aliases(work_id,alias,source)values(wid,'Requiem','verified:https://authority.example/works/requiem');
  ref:=ref||'{"composer":[{"line_id":"L000002","quote":"F. Composer"}],"title":[{"line_id":"L000003","quote":"Requiem"}],
    "catalogue":[{"line_id":"L000003","quote":"K. 626"}],"key":[{"line_id":"L000003","quote":"D minor"}],"movements":[[{"line_id":"L000004","quote":"1. Requiem"}]]}'::jsonb;
  r:=jsonb_set(jsonb_set(jsonb_set(r,'{lines,2,text}','"II F. Composer (1756-1791)"'),'{lines,3,text}','"Requiem in D minor, K. 626"'),'{lines,4,text}','"1. Requiem (Coro)"');
  r:=jsonb_set(r,'{items}',jsonb_build_array(ref));
  e:=e||jsonb_build_object('scope','unknown','reason','scope_requires_review','identity_reason','no_candidate','candidate_ids','[]'::jsonb,
    'suggested_work_id',null,'scoped_work_id',null,'evidence',ref,'fields',jsonb_build_object('title','Requiem','composer','F. Composer',
    'catalogue','K. 626','key','D minor','movements',jsonb_build_array('1. Requiem')));
  proof:=proof||jsonb_build_object('canonical_title','Requiem in D minor','catalogue','K. 626','tonality','D minor','title_forms',jsonb_build_array('Requiem'));
  raw:=proof::text;k:=encode(sha256(convert_to(raw,'UTF8')),'hex');
  pointer:=pointer||jsonb_build_object('result_object_key','extractions/sha256/'||left(k,2)||'/'||k,'result_sha256',k,'proof_utf8',raw);
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('catalogue_repair','parent_work_authority',k,pointer);
  if public.direct_registry_item(r,ref,e,1,wid,k) is distinct from e->'fields' then raise exception 'TEST: source-cited late catalogue match';end if;
  if public.direct_registry_item(jsonb_set(r,'{lines,4,text}','"2. Kyrie"'),ref,e,1,wid,k) is not null
    or public.direct_registry_item(jsonb_set(r,'{lines,3,text}','"Requiem in D major, K. 626"'),ref,e,1,wid,k) is not null
    or public.direct_registry_item(jsonb_set(r,'{lines,3,text}','"Requiem in D minor, K. 626b"'),ref,e,1,wid,k) is not null
    or public.direct_registry_item(r,ref,jsonb_set(e,'{candidate_ids}',jsonb_build_array(another)),1,wid,k) is not null
    or public.direct_registry_item(r,ref,jsonb_set(e,'{identity_reason}','"explicit_key_conflict"'),1,wid,k) is not null
    or public.direct_registry_item(jsonb_set(r,'{lines}',r->'lines'||'[{"text":"arranged by Another Person","page_index":0}]'),ref,e,1,wid,k) is not null
    then raise exception 'TEST: ambiguous link, edition or clipped catalogue/movement';end if;
  update public.works set catalogue='KV. 626' where id=another;
  if public.direct_registry_item(r,ref,e,1,wid,k) is not null then raise exception 'TEST: catalogue collision';end if;
end $test$;
rollback;
select 'PASS: independent parent attribution, exact credit, literal title, duplicate and edition guards' as result;
