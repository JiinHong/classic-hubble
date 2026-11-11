-- The independent calendar dates a particular show; the immutable programme names the excerpts.
create function public.direct_gala_authority(eid uuid,sha text,k text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb; raw text; v jsonb; doc jsonb; nm text;
begin
  if coalesce(k,'')!~'^[0-9a-f]{64}$' then return null;end if;
  select payload into a from public.provider_records where provider='catalogue_repair' and entity_type='dated_gala_authority' and provider_id=k for share;
  raw:=a->>'proof_utf8';
  if raw is null or octet_length(raw) not between 2 and 24576 or encode(sha256(convert_to(raw,'UTF8')),'hex') is distinct from k
    or a->>'result_sha256' is distinct from k or a->>'bucket' is distinct from 'classic-hubble-sources'
    or a->>'result_object_key' is distinct from 'extractions/sha256/'||left(k,2)||'/'||k then return null;end if;
  v:=raw::jsonb;
  if v->>'purpose' is distinct from 'named_gala_excerpts_v1' or v->>'performance_id' is distinct from eid::text
    or v->>'source_sha' is distinct from sha or v->'edition_identified' is distinct from 'false'::jsonb
    or jsonb_typeof(v->'works') is distinct from 'array' or jsonb_array_length(v->'works') not between 1 and 35 then return null;end if;
  foreach nm in array array['calendar','catalogue_source'] loop
    doc:=v->nm;
    if coalesce(doc->>'sha256','')!~'^[0-9a-f]{64}$' or coalesce(doc->>'url','')!~'^https://[^/[:space:]]+/.+'
      or doc->>'original_key' is distinct from 'originals/sha256/'||left(doc->>'sha256',2)||'/'||(doc->>'sha256')
      then return null;end if;
  end loop;
  if v#>>'{calendar,url}'=v#>>'{catalogue_source,url}' or v#>>'{calendar,sha256}'=v#>>'{catalogue_source,sha256}' then return null;end if;
  return v;
exception when data_exception then return null;
end $$;

create function public.direct_gala_window(r jsonb,d jsonb,day date,p jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare ls jsonb:=r->'lines'; n int; s text; i int; prog jsonb:=r->'items'; cnt int; idx int:=0;
  nm text:=p->>'name'; credit text:=p->>'printed_composer'; venue text:=p->>'venue'; hall text:=p->>'hall';
  wk text:=substr('월화수목금토일',extract(isodow from day)::int,1); clock_text text:=p->>'clock'; hh int; mm int;
  mon text:=extract(month from day)::int::text; dy text:=extract(day from day)::int::text;
  event_header text; venue_footer text; t text[]; source_credit text; citeline text;
begin
  if day is null or p is null or r->>'status' is distinct from 'text_extracted' or r->>'coverage' is distinct from 'complete'
    or r->>'extraction_status' is distinct from 'items_extracted' or jsonb_typeof(ls) is distinct from 'array' or jsonb_array_length(ls) not between 8 and 120
    or jsonb_typeof(prog) is distinct from 'array' or jsonb_array_length(prog) not between 1 and 50
    or d->>'prfpdfrom' is distinct from to_char(day,'YYYY.MM.DD') or d->>'prfpdto' is distinct from d->>'prfpdfrom'
    or p->>'date' is distinct from day::text or p->>'event_title' is distinct from d->>'prfnm'
    or coalesce(nm,'')!~'^[A-Za-z][A-Za-z0-9 -]{1,70}$' or coalesce(credit,'')!~'^[가-힣]{2,15}$'
    or coalesce(venue,'')='' or coalesce(hall,'')='' or coalesce(p->>'short_venue','')!~'^[A-Z]{2,8}$'
    or coalesce(clock_text,'')!~'^([01][0-9]|2[0-3]):[0-5][0-9]$' or d->>'dtguidance' is distinct from wk||'요일('||clock_text||')'
    or d->>'fcltynm' is distinct from venue||' ('||hall||')' or right(d->>'prfnm',length(nm)+2) is distinct from ': '||nm then return null;end if;
  hh:=left(clock_text,2)::int;mm:=right(clock_text,2)::int;n:=jsonb_array_length(ls);
  event_header:=ls->0->>'text';t:=regexp_match(event_header,'^([가-힣 ]+갈라쇼) <([A-Za-z0-9 -]+)>$');
  if t is null or t[2]<>nm or replace(d->>'prfnm',' ','') not like '%'||replace(t[1],' ','')||':%' then return null;end if;
  if p#>>'{calendar,year}' is distinct from extract(year from day)::int::text
    or replace(p#>>'{calendar,named_schedule_row,0}',' ','') is distinct from replace(event_header,' ','')
    or p#>>'{calendar,named_schedule_row,1}' is distinct from mon||'. '||dy||'.('||wk||') '||clock_text
    or coalesce(p#>>'{calendar,named_schedule_row,2}','') not in (hall,split_part(hall,' ',1)) then return null;end if;
  t:=regexp_match(ls->1->>'text','^([0-9]{1,2})\. *([0-9]{1,2})\. *([월화수목금토일]) (오전|오후) ([1-9]|1[012])시( ([0-5]?[0-9])분)?$');
  if t is null or t[1]::int<>mon::int or t[2]::int<>dy::int or t[3]<>wk or
    (t[5]::int%12+case when t[4]='오후' then 12 else 0 end)<>hh or coalesce(t[7]::int,0)<>mm
    or ls->2->>'text' is distinct from (p->>'short_venue')||' '||hall then return null;end if;
  source_credit:=ls->3->>'text';
  if coalesce(source_credit,'')!~'^([가-힣 ]+)은 오직 [가-힣]+의 작품만으로 채우는 특별한 무대 <[A-Za-z0-9 -]+>를 선보입니다\.$'
    or strpos(source_credit,' 오직 '||credit||'의 작품만으로 ')=0 or strpos(source_credit,'<'||nm||'>')=0
    or ls->4->>'text' is distinct from nm||' Programs' then return null;end if;
  if coalesce(p->>'festival_heading','')!~('^'||extract(year from day)::int||' [A-Z][A-Z ]+ FESTIVAL$')
    or ls->(n-2)->>'text' is distinct from p->>'festival_heading' then return null;end if;
  venue_footer:=venue||' '||hall||' '||mon||'. '||dy||'. '||wk||' '||clock_text||' '||event_header;
  if ls->(n-1)->>'text' is distinct from venue_footer then return null;end if;
  for i in 0..n-1 loop
    s:=ls->i->>'text';
    if ls->i->>'page_index' is distinct from '0' or coalesce(s,'')='' then return null;end if;
    if i<=4 or i>=n-2 then continue;end if;
    if s ~ '^(Intermission )?[1-9]부$' then continue;end if;
    if s ~* '(예매|변경|취소|프로필|공연 이력|프로그램 해설|ticket|booking|cancel|reschedul|profile|program(me)? notes|[0-9]{1,2} *[./월-] *[0-9]{1,2})' then return null;end if;
    citeline:='L'||lpad(i::text,6,'0');
    select count(*) into cnt from jsonb_array_elements(prog) e where e#>>'{title,0,line_id}'=citeline;
    if cnt<>1 or prog->idx#>>'{title,0,line_id}' is distinct from citeline then return null;end if;
    idx:=idx+1;
  end loop;
  if idx<>jsonb_array_length(prog) then return null;end if;
  return p||jsonb_build_object('start_line',4,'end_line',n-2);
exception when data_exception then return null;
end $$;

create function public.direct_gala_item(r jsonb,ref jsonb,f jsonb,p jsonb,wid uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare w public.works; author public.composers; x jsonb; n int; l text; i int; parent text; part text; s text; k int; tail text;
begin
  if p is null or wid is null or f->'evidence' is distinct from ref or f->>'reason' is distinct from 'scope_requires_review'
    or f->>'identity_reason' is distinct from 'no_candidate' or f->'candidate_ids' is distinct from '[]'::jsonb
    or f->>'suggested_work_id' is not null or f->>'scoped_work_id' is not null or f?'derived_from'
    or f->>'context' is distinct from 'program' or ref->>'context' is distinct from 'program'
    or f->>'model_scope' is distinct from 'excerpt' or f->>'scope' is distinct from 'excerpt' or ref->>'scope' is distinct from 'excerpt'
    or ref->'key' is distinct from 'null'::jsonb or ref->'catalogue' is distinct from 'null'::jsonb then return null;end if;
  parent:=ref#>>'{title,0,quote}';l:=ref#>>'{title,0,line_id}';part:=ref#>>'{movements,0,0,quote}';
  if coalesce(l,'')!~'^L[0-9]{6}$' or coalesce(parent,'')='' or coalesce(part,'')='' or part=parent
    or ref->'composer' is distinct from jsonb_build_array(jsonb_build_object('line_id','L000003','quote',p->>'printed_composer'))
    or ref->'title' is distinct from jsonb_build_array(jsonb_build_object('line_id',l,'quote',parent))
    or ref->'movements' is distinct from jsonb_build_array(jsonb_build_array(jsonb_build_object('line_id',l,'quote',part)))
    or f->'fields' is distinct from jsonb_build_object('composer',p->>'printed_composer','title',parent,'movements',jsonb_build_array(part),'catalogue',null,'key',null) then return null;end if;
  i:=substr(l,2)::int;
  if i<=(p->>'start_line')::int or i>=(p->>'end_line')::int then return null;end if;
  s:=r->'lines'->i->>'text';k:=strpos(s,' '||parent||' ');
  if s is null or k<2 or left(s,k-1)!~'^[가-힣 ]+$' then return null;end if;
  tail:=substr(s,k+length(parent)+2);
  if not(tail=part or (right(tail,length(part)+1)=' '||part and left(tail,length(tail)-length(part)-1) ~ '[가-힣]')) then return null;end if;
  select count(*),jsonb_agg(v)->0 into n,x from jsonb_array_elements(p->'works') v where v->>'printed_title'=parent;
  if n<>1 or x->>'work_id' is distinct from wid::text or jsonb_typeof(p#>'{catalogue_source,printed_names}') is distinct from 'array'
    or not exists(select from jsonb_array_elements_text(p#>'{catalogue_source,printed_names}') v where lower(v)=lower(parent))
    or not exists(select from jsonb_array_elements_text(p#>'{catalogue_source,printed_names}') v where lower(v)=lower(x->>'canonical'))
    then return null;end if;
  select * into w from public.works where id=wid for share;
  if not found or w.composer_id::text is distinct from p->>'composer_id' or w.title is distinct from x->>'canonical'
    or w.slug is distinct from x->>'slug' then return null;end if;
  select * into author from public.composers where id=w.composer_id for share;
  if not found or author.name is distinct from p->>'composer' or author.name_ko is distinct from p->>'composer_ko'
    or split_part(author.name_ko,' ',-1) is distinct from p->>'printed_composer'
    or (lower(w.title) is distinct from lower(parent) and not exists(select from public.work_aliases a where a.work_id=wid and lower(a.alias)=lower(parent)))
    or exists(select from public.works b join public.composers ac on ac.id=b.composer_id where b.id<>wid and
      (ac.id=author.id or split_part(ac.name_ko,' ',-1)=p->>'printed_composer')
      and (lower(b.title)=lower(parent) or lower(b.title_ko)=lower(parent) or exists(select from public.work_aliases a where a.work_id=b.id and lower(a.alias)=lower(parent))))
    then return null;end if;
  return f->'fields';
exception when data_exception then return null;
end $$;

revoke all on function public.direct_gala_authority(uuid,text,text),public.direct_gala_window(jsonb,jsonb,date,jsonb),public.direct_gala_item(jsonb,jsonb,jsonb,jsonb,uuid) from public,anon,authenticated;
grant execute on function public.direct_gala_authority(uuid,text,text),public.direct_gala_window(jsonb,jsonb,date,jsonb),public.direct_gala_item(jsonb,jsonb,jsonb,jsonb,uuid) to service_role;

do $migration$
declare def text:=pg_get_functiondef('public.publish_direct_movement_program(uuid,jsonb,jsonb,jsonb)'::regprocedure);
  search text[]:=array[
    '  orig text;', 'header:=public.direct_movement_program_section(r,detail,p.starts_on);',
    '    if p_document->>''identity_mode''=''independent_parent_registry_v1'' then',
    'history:=jsonb_build_object(''version'',case when', '  insert into public.provider_records(provider,entity_type,provider_id,payload)values(''codex_vision'',''movement_program_publication'''];
  repl text[]:=array[
    '  gala jsonb; orig text;',
    $date$if p_document->>'identity_mode'='named_gala_excerpts_v1' then
    gala:=public.direct_gala_window(r,detail,p.starts_on,public.direct_gala_authority(p_id,orig,p_document->>'gala_key'));
    if gala is null or jsonb_array_length(p_candidates) is distinct from jsonb_array_length(r->'items') then return '{"status":"gala_authority_or_sections_unverified","items":0}';end if;
    header:=(gala->>'start_line')::int;
  else header:=public.direct_movement_program_section(r,detail,p.starts_on);end if;$date$,
    $gala$    if gala is not null then
      fields:=public.direct_gala_item(r,ref,e,gala,wid);
      if n<>1 or fields is null or scope<>'excerpt' then return '{"status":"gala_excerpt_unverified","items":0}';end if;
      items:=items||jsonb_build_array(jsonb_build_object('position',idx,'work_id',wid,'composer_name',fields->>'composer',
        'display_title',fields->>'title','performed_scope','excerpt','scope_details',fields->'movements','source_url',url));continue;
    elsif p_document->>'identity_mode'='independent_parent_registry_v1' then$gala$,
    'history:=jsonb_build_object(''version'',case when gala is not null then ''direct-named-gala-v1'' when',
    $audit$  if gala is not null then history:=history||jsonb_build_object('gala_key',p_document->>'gala_key');end if;
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('codex_vision','movement_program_publication'$audit$];
  i int;
begin
  for i in 1..cardinality(search) loop
    if length(def)-length(replace(def,search[i],''))<>length(search[i]) then raise exception 'Unexpected movement RPC anchor %',i;end if;
    def:=replace(def,search[i],repl[i]);
  end loop;
  execute def;
end $migration$;
notify pgrst,'reload schema';
