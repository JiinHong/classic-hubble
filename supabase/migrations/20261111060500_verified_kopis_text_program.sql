-- A saved concert cover identifies the event. Work titles are from the official
-- typed KOPIS programme, never from the cover, a soloist list, or suggested search results.
create function public.kopis_text_blocks(sty text,style text) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare ls text[]; body text; s text; a text[]; m text[]; credit text; title text; outp jsonb:='[]';
begin
  if sty is null or octet_length(sty)>32000 or style not in ('bullets','stacked') then return null;end if;
  ls:=string_to_array(replace(sty,E'\r\n',E'\n'),E'\n');
  if cardinality(ls) not between 2 and 200 or btrim(ls[1])<>'[PROGRAM]' then return null;end if;
  body:=array_to_string(ls[2:cardinality(ls)],E'\n');if body ~ '[][<>]' then return null;end if;
  foreach s in array case style when 'bullets' then string_to_array(body,E'\n') else regexp_split_to_array(btrim(body,E' \t\n'),E'\n[ \t]*\n') end loop
    s:=btrim(s,E' \t\n');if s='' then continue;end if;credit:=null;title:=null;
    if style='bullets' then
      if left(s,1)<>'*' then return null;end if;
      a:=string_to_array(btrim(substr(s,2)),' / ');
      if cardinality(a)=2 and btrim(a[1]) ~ '^[A-Za-zÀ-ÖØ-öø-ÿ가-힣][A-Za-zÀ-ÖØ-öø-ÿ가-힣 .''-]{0,90}$' then credit:=btrim(a[1]);title:=btrim(a[2]);end if;
    else
      if s='INTERMISSION' then continue;end if;
      a:=array(select btrim(v,E' \t') from unnest(string_to_array(s,E'\n')) v where btrim(v,E' \t')<>'');
      if cardinality(a)=1 then return null;end if;
      m:=regexp_match(a[1],'^([A-Za-zÀ-ÖØ-öø-ÿ가-힣][A-Za-zÀ-ÖØ-öø-ÿ가-힣 .''-]{0,90}?)(?: \((?:b\. [0-9]{4}|[0-9]{4}-[0-9]{4})\))?(?: \(작사 : [가-힣]{2,8}\))?$');
      if m is not null and (cardinality(a)=2 or (cardinality(a)=3 and a[3] ~ '^(Soprano|Saxophone|Trumpet) [가-힣]{2,8}(, [가-힣]{2,8})*$')) then credit:=m[1];title:=a[2];end if;
    end if;
    outp:=outp||jsonb_build_array(case when coalesce(title,'')<>'' and credit is not null and s !~* '\m(arr\.|arranged|arrangement|arranger)|편곡|작품해설|예매'
                              then jsonb_build_array(credit,title) end);
  end loop;
  if jsonb_array_length(outp) not between 1 and 60 then return null;end if;return outp;
end $$;

create function public.kopis_text_cover(r jsonb,a jsonb,day date) returns boolean
language plpgsql immutable security invoker set search_path='' as $$
declare ls text[]; n int; dow int:=extract(isodow from day)::int; k text:=substr('월화수목금토일',dow,1); t text[]; hh int; mm int;
  mo int:=extract(month from day)::int; dd int:=extract(day from day)::int; yr int:=extract(year from day)::int; title text; v text;
begin
  if day is null or r->>'coverage' is distinct from 'complete' or r->>'status' is distinct from 'text_extracted' or r->>'extraction_status' is distinct from 'no_program_identified'
     or r->'items' is distinct from '[]'::jsonb or jsonb_typeof(r->'lines') is distinct from 'array'
     or exists(select from jsonb_array_elements(r->'lines') l where l->>'page_index' is distinct from '0' or coalesce(l->>'text','')='') then return false;end if;
  ls:=array(select l->>'text' from jsonb_array_elements(r->'lines') l);n:=cardinality(ls);
  t:=regexp_match(a->>'schedule','^'||k||'요일\(([01][0-9]|2[0-3]):([0-5][0-9])\)$');if t is null or n not between 6 and 18 then return false;end if;
  hh:=t[1]::int;mm:=t[2]::int;
  if a->>'style'='bullets' then
    if a->>'venue' is distinct from '쌀롱드무지끄 (쌀롱드무지끄)' or left(a->>'title',length('쌀롱드무지끄, ')) is distinct from '쌀롱드무지끄, ' then return false;end if;
    title:=substr(a->>'title',length('쌀롱드무지끄, ')+1);v:=' ('||mo||'.'||dd||')';
    if right(title,length(v))=v then title:=left(title,-length(v));end if;
    return n>=8 and ls[1]='Salon de Musique' and regexp_replace(lower(replace(title,'Ⅱ','II')),'^the ','')=lower(replace(ls[2],'Ⅱ','II'))
      and ls[3:7]=array[(array['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'])[mo]||' '||yr,mo||' / '||dd,yr::text,
        (array['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])[dow]||' '||t[1]||':'||t[2],'Line up']
      and not exists(select from unnest(ls[8:n]) x where x !~ '^((Violin|Piano|Cello) [가-힣]{2,8}|Ticket OPEN *: .+)$');
  elsif a->>'style'='stacked' then
    return n>=8 and ls[1]||' '||ls[2]=regexp_replace(a->>'title',' \[[^][]+\]$','') and ls[3:4]=array['With','SEOULKUNST ORCHESTRA']
      and not exists(select from unnest(ls[5:n-3]) x where strpos(x,' | ')=0 or x~'[0-9]')
      and ls[n-2:n]=array[yr||'. '||mo||'. '||dd||'. ('||k||')',(case when hh<12 then '오전' else '오후' end)||' '||case when hh%12=0 then 12 else hh%12 end||'시 '||mm||'분',split_part(a->>'venue',' (',1)];
  end if;return false;
exception when data_exception then return false;
end $$;

create function public.kopis_text_program_items(sty text,a jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare pieces jsonb:=public.kopis_text_blocks(sty,a->>'style');r jsonb;w public.works;c public.composers;pos int;prev int:=-1;seen uuid[]:='{}';s jsonb;
  printed text;canonical text;witness text;credit text;creditw text;root text;part text[];suffix text;keym text[];number text[];dbn text[];typ text;src jsonb;outp jsonb:='[]';
  op_rx text:='op\.?\s*([0-9]+[a-z]?)(?:,\s*(?:no\.?\s*)?([0-9]+))?';
begin
  if pieces is null or jsonb_typeof(a->'rows') is distinct from 'array' or jsonb_array_length(a->'rows') not between 1 and 60 then return null;end if;
  for r in select value from jsonb_array_elements(a->'rows') loop
    pos:=(r->>'position')::int;s:=pieces->pos;
    if jsonb_typeof(r->'position') is distinct from 'number' or coalesce(r->>'position','')!~'^[0-9]+$' or pos is null or pos<=prev or pos>=jsonb_array_length(pieces) or jsonb_typeof(s) is distinct from 'array'
      or s->0 is distinct from r->'credit' or s->1 is distinct from r->'title' then return null;end if;prev:=pos;
    src:=a->'sources'->(r->>'source');
    if coalesce(src->>'sha','')!~'^[a-f0-9]{64}$' or coalesce(src->>'url','')!~'^https://[^/[:space:]]+/.+' then return null;end if;
    select * into w from public.works where id=(r->>'work_id')::uuid for share;
    if not found or w.id=any(seen) or w.slug is distinct from r->>'slug' or w.title is distinct from r->>'canonical_title' or w.catalogue is distinct from r->>'catalogue'
      or w.composer_id::text is distinct from r->>'composer_id' then return null;end if;
    seen:=array_append(seen,w.id);select * into c from public.composers where id=w.composer_id for share;
    if not found or c.name is distinct from r->>'composer' then return null;end if;
    credit:=replace(lower(r->>'credit'),'é','e');canonical:=replace(lower(c.name),'é','e');part:=string_to_array(canonical,' ');creditw:=replace(lower(r->>'credit_witness'),'é','e');
    if coalesce(strpos(creditw,part[cardinality(part)]),0)=0
      or not (credit=canonical or (credit ~ '^[a-z]\. [^ .]+$' and cardinality(part)>=2 and substr(credit,4)=part[cardinality(part)]
            and exists(select from unnest(part[1:cardinality(part)-1]) g where left(g,1)=left(credit,1)))) then return null;end if;
    printed:=replace(lower(r->>'title'),'é','e');canonical:=replace(lower(w.title),'é','e');witness:=replace(lower(r->>'work_witness'),'é','e');typ:=r->>'scope';
    if coalesce(printed,'')='' or coalesce(canonical,'')='' or coalesce(witness,'')='' then return null;end if;
    if typ='excerpt' then
      if r->'detail' is distinct from r->'title' or printed=canonical or strpos(witness,printed)=0 or strpos(witness,canonical)=0 then return null;end if;
    elsif typ='unknown' then
      if r->'detail' is distinct from 'null'::jsonb then return null;end if;
      part:=string_to_array(printed,' 中 ');if cardinality(part)>2 or (cardinality(part)=2 and (strpos(witness,part[1])=0 or part[2]<>canonical)) then return null;end if;
      part:=string_to_array(part[cardinality(part)],', op. ');if cardinality(part)>2 then return null;end if;root:=part[1];suffix:=part[2];
      if suffix is not null then
        number:=regexp_match('op. '||suffix,'^'||op_rx||'$');dbn:=regexp_match(lower(w.catalogue),'^'||op_rx||'$');
        if number is null or dbn is null or number[1]<>dbn[1] or (dbn[2] is not null and number[2] is distinct from dbn[2]) or
          (select jsonb_agg(to_jsonb(v)) from regexp_matches(witness,'\m'||op_rx||'\M','g') v) is distinct from jsonb_build_array(to_jsonb(number)) then return null;end if;
      end if;
      if root<>canonical and not(length(root)>=8 and starts_with(canonical,root||' in ')) then return null;end if;
      if strpos(witness,root)=0 then
        keym:=regexp_match(root,'^violin sonata no\. [1-9][0-9]? in ([a-g] (major|minor))$');
        if keym is null or suffix is null or strpos(witness,'violin sonata')=0 or strpos(witness,keym[1])=0 then return null;end if;
      end if;
      if exists(select from public.works w2 where w2.composer_id=c.id and w2.id<>w.id and
        (lower(w2.title)=root or (length(root)>=8 and starts_with(lower(w2.title),root||' in '))) and (suffix is null or w2.catalogue=w.catalogue)) then return null;end if;
    else return null;end if;
    outp:=outp||jsonb_build_array(jsonb_build_object('position',pos,'work_id',w.id,'composer_name',c.name,'display_title',r->>'title','performed_scope',typ,
      'scope_details',case when typ='excerpt' then jsonb_build_array(r->'detail') else '[]'::jsonb end));
  end loop;return outp;
exception when data_exception then return null;
end $$;

create function public.publish_kopis_text_program(p_id uuid,p_document jsonb,p_expected jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare p public.performances; d jsonb; src jsonb; ptr jsonb; ref jsonb; a jsonb; env jsonb; srcurl text; publicurl text; sha text:=p_document->>'sha';
  raw text:=p_document->>'envelope_utf8'; envsha text; k text:=p_document->>'authority'; ar text; stysha text; program jsonb; before_rows jsonb; fresh jsonb; checked timestamptz;
begin
  select * into p from public.performances where id=p_id for update;
  if not found or coalesce(p.kopis_performance_id,'')!~'^PF[0-9]+$' or p.starts_on is null or p.starts_on is distinct from p.ends_on
     or cardinality(p.intro_image_urls) is distinct from 1 then return '{"status":"date_or_source_binding_required","items":0}';end if;
  srcurl:=p.intro_image_urls[1];publicurl:='https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id='||p.kopis_performance_id;
  if raw is null or octet_length(raw) not between 1 and 524288 or coalesce(k,'')!~'^[a-f0-9]{64}$' or coalesce(sha,'')!~'^[a-f0-9]{64}$' then return '{"status":"stale_evidence","items":0}';end if;
  select payload into src from public.provider_records where provider='r2' and entity_type='source_archive' and provider_id=encode(sha256(convert_to(srcurl,'UTF8')),'hex') for share;
  select payload into ptr from public.provider_records where provider='codex_vision' and entity_type='direct_reading' and provider_id=p_document->>'reading_key' for share;
  envsha:=encode(sha256(convert_to(raw,'UTF8')),'hex');env:=raw::jsonb;
  if src->>'source_url' is distinct from srcurl or src->>'bucket' is distinct from 'classic-hubble-sources' or src->>'sha256' is distinct from sha
    or src->>'object_key' is distinct from 'originals/sha256/'||left(sha,2)||'/'||sha or not coalesce(src->'performance_ids' ? p_id::text,false)
    or ptr->>'result_sha256' is distinct from envsha or ptr->>'result_object_key' is distinct from 'extractions/sha256/'||left(envsha,2)||'/'||envsha
    or ptr->'bucket' is distinct from src->'bucket' or ptr->'source_object_key' is distinct from src->'object_key' or ptr->>'source_sha256' is distinct from sha
    or ptr->>'pipeline_version' is distinct from 'codex-direct-vision-v1' or ptr->>'method' is distinct from 'chat_model_direct_image_reading'
    or ptr->>'coverage' is distinct from 'complete' or ptr->>'status' is distinct from 'text_extracted' or coalesce(ptr->>'reading_sha256','')!~'^[a-f0-9]{64}$'
    or env->'source_object_key' is distinct from src->'object_key' or env->'bucket' is distinct from src->'bucket' or env->'reading_sha256' is distinct from ptr->'reading_sha256'
    or env->'pipeline_version' is distinct from ptr->'pipeline_version' or env->'method' is distinct from ptr->'method'
    or env->>'source_sha256' is distinct from sha or env#>>'{reading,source_sha256}' is distinct from sha then return '{"status":"stale_evidence","items":0}';end if;
  select payload into ref from public.provider_records where provider='catalogue_repair' and entity_type='typed_block_authority' and provider_id=k for share;ar:=ref->>'proof_utf8';
  if ar is null or octet_length(ar) not between 2 and 96000 or encode(sha256(convert_to(ar,'UTF8')),'hex') is distinct from k or ref->>'result_sha256' is distinct from k
    or ref->'bucket' is distinct from src->'bucket' or ref->>'result_object_key' is distinct from 'extractions/sha256/'||left(k,2)||'/'||k then return '{"status":"missing_work_evidence","items":0}';end if;
  a:=ar::jsonb;select payload into d from public.provider_records where provider='kopis' and entity_type='performance_detail' and provider_id=p.kopis_performance_id for share;
  stysha:=encode(sha256(convert_to(d->>'sty','UTF8')),'hex');
  if a->>'version' is distinct from 'kopis-typed-blocks-v1' or a->>'id' is distinct from p_id::text or a->>'kopis' is distinct from p.kopis_performance_id
    or d->>'mt20id' is distinct from p.kopis_performance_id or a->>'title' is distinct from p.title or d->>'prfnm' is distinct from p.title
    or a->>'day' is distinct from p.starts_on::text or d->>'prfpdfrom' is distinct from to_char(p.starts_on,'YYYY.MM.DD') or d->>'prfpdto' is distinct from d->>'prfpdfrom'
    or a->'venue' is distinct from d->'fcltynm' or a->'schedule' is distinct from d->'dtguidance'
    or (d#>'{styurls,styurl}' is distinct from to_jsonb(srcurl) and d#>'{styurls,styurl}' is distinct from to_jsonb(p.intro_image_urls))
    or a->>'cover_sha' is distinct from sha or a->>'envelope_sha' is distinct from envsha or stysha is null or a->>'sty_sha' is distinct from stysha
    or a->'sty' is distinct from d->'sty' or d->>'sty' is distinct from p.synopsis then return '{"status":"stale_kopis_detail","items":0}';end if;
  if public.kopis_text_cover(env->'reading',a,p.starts_on) is not true then return '{"status":"cover_binding_unverified","items":0}';end if;
  program:=public.kopis_text_program_items(d->>'sty',a);if program is null then return '{"status":"work_evidence_unverified","items":0}';end if;
  if p_expected is not null then
    select jsonb_object_agg(x,d->x) into fresh from unnest(array['mt20id','prfnm','prfpdfrom','prfpdto','dtguidance','fcltynm','styurls']) x;
    checked:=(p_document->>'checked_at')::timestamptz;
    if checked is null or checked not between now()-interval '5 minutes' and now()+interval '1 minute' or p_document->'live_detail' is distinct from fresh
      or p_document->>'live_sty_sha' is distinct from stysha or p_document->>'live_sha' is distinct from sha or p_document->'content_type' is distinct from src->'content_type'
      or p_expected is distinct from program then return '{"status":"live_sources_or_preview_changed","items":0}';end if;
  end if;
  perform 1 from public.program_items where performance_id=p_id for update;
  select coalesce(jsonb_agg(jsonb_build_object('position',position,'work_id',work_id,'composer_name',composer_name,'display_title',display_title,'performed_scope',performed_scope,
      'scope_details',scope_details) order by position),'[]') into before_rows from public.program_items where performance_id=p_id;
  if before_rows=program and p.program_status::text='partially_confirmed' and p.program_source_url=publicurl and p.program_image_urls=p.intro_image_urls
     and not exists(select from public.program_items where performance_id=p_id and (source_provider is distinct from 'kopis' or source_type::text is distinct from 'official' or source_url is distinct from publicurl))
     and exists(select from public.provider_records where provider='kopis' and entity_type='typed_block_publication' and provider_id=p_id::text||':'||k)
     then return jsonb_build_object('status','unchanged','items',jsonb_array_length(program));end if;
  if before_rows<>'[]'::jsonb or p.program_source_url is not null or p.program_status::text is distinct from 'unknown' or cardinality(p.program_image_urls)>0
     then return '{"status":"existing_program_preserved","items":0}';end if;
  if p_expected is null then return jsonb_build_object('status','ready','items',jsonb_array_length(program),'program',program);end if;
  insert into public.provider_records(provider,entity_type,provider_id,payload)values('kopis','typed_block_publication',p_id::text||':'||k,
    jsonb_build_object('performance_id',p_id,'version',a->>'version','before_performance',to_jsonb(p),'before',before_rows,'after',program,'authority',k,'source_sha',sha,
      'envelope_sha',envsha,'sty_sha',stysha,'public_url',publicurl,'date',p.starts_on,'checked_at',checked,'cover_contribution','event_identity_only','held',a->'held'));
  insert into public.program_items(performance_id,position,composer_name,display_title,work_id,performed_scope,scope_details,source_type,source_provider,source_url)
     select p_id,(v->>'position')::int,v->>'composer_name',v->>'display_title',(v->>'work_id')::uuid,v->>'performed_scope',v->'scope_details','official','kopis',publicurl from jsonb_array_elements(program) v;
  update public.performances set program_status='partially_confirmed',program_source_url=publicurl,program_image_urls=p.intro_image_urls,program_source_updated_at=checked where id=p_id;
  return jsonb_build_object('status','published','items',jsonb_array_length(program));
exception when data_exception then return '{"status":"invalid_evidence","items":0}';
end $$;
revoke all on function public.kopis_text_blocks(text,text),public.kopis_text_cover(jsonb,jsonb,date),public.kopis_text_program_items(text,jsonb),public.publish_kopis_text_program(uuid,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.kopis_text_blocks(text,text),public.kopis_text_cover(jsonb,jsonb,date),public.kopis_text_program_items(text,jsonb),public.publish_kopis_text_program(uuid,jsonb,jsonb) to service_role;
notify pgrst,'reload schema';
