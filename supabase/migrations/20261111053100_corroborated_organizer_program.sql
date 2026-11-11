-- Two independent sources: the organizer supplies the programme; the saved poster supplies
-- a separate event and item cross-check. Neither source may overwrite a pre-existing programme.
create function public.organizer_quote(ls jsonb, spans jsonb) returns text
language plpgsql immutable security invoker set search_path='' as $$
declare q jsonb; n int; v text; s text;
begin
  if jsonb_typeof(spans) is distinct from 'array' or jsonb_array_length(spans)<>1 then return null;end if;
  q:=spans->0;v:=q->>'quote';
  if coalesce(q->>'line_id','') !~ '^L[0-9]{6}$' or coalesce(v,'')='' then return null;end if;
  n:=substr(q->>'line_id',2)::int;s:=ls->n->>'text';
  if ls->n->>'page_index' is distinct from '0' or s is null or strpos(s,v)=0 then return null;end if;
  return v;
end $$;

create function public.organizer_program_items(r jsonb, a jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
<<build_rows>>
declare row jsonb; ref jsonb; piece jsonb; v text; parts jsonb; ls jsonb:=r->'lines'; songs jsonb:=a#>'{event,program}';
  fmt text:=a->>'format'; w public.works; c public.composers; i int; n int; prev int:=-1; prev_line int:=-1;
  title text; credit text; ot text; oc text; current_program jsonb:='[]'::jsonb; extra text; psalm boolean;
begin
  if fmt is null or fmt not in ('national_theatre','paju_hwp') or r->>'status' is distinct from 'text_extracted' or r->>'extraction_status' is distinct from 'items_extracted'
    or coalesce(r->>'coverage','') not in ('partial','complete') or jsonb_typeof(r->'items') is distinct from 'array'
    or jsonb_typeof(ls) is distinct from 'array' or jsonb_array_length(ls) not between 2 and 250
    or jsonb_typeof(a->'rows') is distinct from 'array' or jsonb_array_length(a->'rows') not between 1 and 50 then return null;end if;
  for row in select value from jsonb_array_elements(a->'rows') loop
    if coalesce(row->>'index','') !~ '^(0|[1-9][0-9]?)$' or coalesce(row->>'line','') !~ '^(0|[1-9][0-9]{0,4})$' then return null;end if;
    i:=(row->>'index')::int;n:=(row->>'line')::int;
    if i<=prev or i>=jsonb_array_length(r->'items') or n<=prev_line then return null;end if;
    prev:=i;prev_line:=n;ref:=r->'items'->i;
    if ref->>'context' is distinct from 'program' or coalesce(ref->>'scope','') not in ('unknown','full_work')
      or ref->'key' is distinct from 'null'::jsonb or ref->'catalogue' is distinct from 'null'::jsonb
      or jsonb_typeof(ref->'movements') is distinct from 'array' or jsonb_array_length(ref->'movements')>50 then return null;end if;
    title:=public.organizer_quote(ls,ref->'title');credit:=public.organizer_quote(ls,ref->'composer');
    if title is null or credit is null or row->>'poster_title' is distinct from title or row->>'poster_credit' is distinct from credit then return null;end if;
    ot:=row->>'official_title';oc:=row->>'official_credit';parts:='[]';
    for piece in select value from jsonb_array_elements(ref->'movements') loop
      v:=public.organizer_quote(ls,piece);if v is null then return null;end if;parts:=parts||jsonb_build_array(v);
    end loop;
    select * into w from public.works where id=(row->>'work_id')::uuid for share;
    if not found or w.title is distinct from row->>'canonical_title' or w.slug is distinct from row->>'slug' or w.composer_id::text is distinct from row->>'composer_id' then return null;end if;
    select * into c from public.composers where id=w.composer_id for share;
    if not found or c.name is distinct from row->>'canonical_credit' then return null;end if;
    psalm:=fmt='national_theatre' and title='Der 42. Psalm' and c.name='Felix Mendelssohn' and credit='Felix Mendelssohn Bartholdy'
      and w.title='Psalm 42 in F major' and w.catalogue='Op. 42' and row->>'independent_source'='psalm'
      and a#>>'{sources,psalm,url}' like 'https://www.carus-verlag.com/%' and jsonb_array_length(parts)=7;
    if coalesce(psalm,false) and exists(select from jsonb_array_elements(ref->'movements') with ordinality g(v,j)
      where substr(g.v#>>'{0,line_id}',2)::int<>substr(ref#>>'{title,0,line_id}',2)::int+j or
        g.v#>>'{0,quote}' not like (array['I','II','III','IV','V','VI','VII'])[j::int]||'. %') then return null;end if;
    if not coalesce(psalm,false) and lower(title) is distinct from lower(w.title) and lower(title) is distinct from lower(w.title_ko)
      and not exists(select from public.work_aliases y where y.work_id=w.id and lower(y.alias)=lower(build_rows.title)) then return null;end if;
    if exists(select from public.works z where z.composer_id=c.id and z.id<>w.id and
      (lower(build_rows.title) in (lower(z.title),lower(z.title_ko)) or lower(z.title)=lower(w.title) or (coalesce(psalm,false) and z.catalogue=w.catalogue)
       or exists(select from public.work_aliases y where y.work_id=z.id and lower(y.alias)=lower(build_rows.title)))) then return null;end if;
    if fmt='national_theatre' then
      if r->>'coverage'<>'complete' or jsonb_typeof(songs) is distinct from 'array' or n>=jsonb_array_length(songs) or ot is null or oc is distinct from credit
        or songs->>n is distinct from ot||' ❘ '||oc or (oc is distinct from c.name and not coalesce(psalm,false)) then return null;end if;
      if lower(ot)<>lower(title) then
        extra:=substring(ot from length(title)+1);
        if lower(left(ot,length(title)))<>lower(title) or extra !~ '^ [가-힣][가-힣 ]*$' then return null;end if;
      end if;
      if not coalesce(psalm,false) and (parts<>'[]'::jsonb or ref#>>'{title,0,line_id}' is distinct from ref#>>'{composer,0,line_id}'
        or ls->(substr(ref#>>'{title,0,line_id}',2)::int)->>'text' is distinct from title||' '||credit) then return null;end if;
    else
      if i<>0 or jsonb_array_length(r->'items')<>1 or parts is distinct from '["제1부 | Erster Teil","제2부 | Zweiter Teil"]'::jsonb
        or ref->>'scope' is distinct from 'unknown' or ot is distinct from title or credit is distinct from '멘델스존'
        or oc is distinct from c.name_ko or c.name is distinct from 'Felix Mendelssohn' or c.name_ko is distinct from '펠릭스 멘델스존'
        or left(coalesce(a#>>'{notice,credit}',''),length('독일의 작곡가 '||oc||'이 작곡한 ‘'||ot||'’는 ')) is distinct from '독일의 작곡가 '||oc||'이 작곡한 ‘'||ot||'’는 '
        or position('정기공연 오라토리오 ‘'||ot||'’를 선보인다.' in coalesce(a#>>'{notice,dated}',''))=0
        or a#>>'{notice,paragraph_indices,1}' is distinct from n::text then return null;end if;
    end if;
    current_program:=current_program||jsonb_build_array(jsonb_build_object('position',i,'work_id',w.id,'composer_name',c.name,'display_title',title,'performed_scope','unknown','scope_details',parts));
  end loop;
  return current_program;
exception when data_exception then return null;
end $$;

create function public.organizer_program_event(a jsonb,d jsonb,r jsonb,day date) returns boolean
language plpgsql immutable security invoker set search_path='' as $$
declare e jsonb:=a->'event';z jsonb;ls jsonb:=r->'lines';clock text:=e->>'clock';hall text:=e->>'hall';nm text:=d->>'prfnm';room text[];
 k text; rawurl text; weekday int:=extract(isodow from day)::int; ko text:=substr('월화수목금토일',weekday,1);hh int; mm int; parts text[]; digest_ text;
begin
 if day is null or coalesce(clock,'') !~ '^([01][0-9]|2[0-3]):[0-5][0-9]$' or coalesce(hall,'')='' or e->>'day' is distinct from day::text
   or a->>'date' is distinct from day::text or a->>'kopis_title' is distinct from nm or a->>'kopis_venue' is distinct from d->>'fcltynm'
   or d->>'prfpdfrom' is distinct from to_char(day,'YYYY.MM.DD') or d->>'prfpdto' is distinct from d->>'prfpdfrom'
   or d->>'dtguidance' is distinct from ko||'요일('||clock||')' or jsonb_typeof(a->'sources') is distinct from 'object' then return false;end if;
 hh:=left(clock,2)::int;mm:=right(clock,2)::int;
 for k,z in select key,value from jsonb_each(a->'sources') loop
   if coalesce(z->>'sha','') !~ '^[a-f0-9]{64}$' or coalesce(z->>'url','') !~ '^https://[^/@[:space:]]+/.+' then return false;end if;
 end loop;
 rawurl:=a#>>'{sources,venue,url}';if rawurl is null or a->>'public_url' is distinct from rawurl then return false;end if;
 room:=regexp_match(d->>'fcltynm','^([^()]+) \(([^()]+)\)$');if room is null then return false;end if;
 if a->>'format'='national_theatre' then
   if rawurl !~ '^https://www\.ntok\.go\.kr/ntok/pm/prfmng/performanceDetail\.do\?mi=21009&perfId=[0-9]+$'
     or room[1]<>'국립극장' or room[2]<>hall or r->>'coverage' is distinct from 'complete'
     or ls->0->>'text' is distinct from to_char(day,'YYYY.MM.DD')||' '||(array['MON','TUE','WED','THU','FRI','SAT','SUN'])[weekday]||' '||
       (case when hh%12=0 then 12 else hh%12 end)::text||':'||right(clock,2)||(case when hh>=12 then ' PM' else ' AM' end)
     or ls->1->>'text' is distinct from room[1]||' '||hall or coalesce(ls->3->>'text','') !~* '^PROGRAM( |$)'
     or nm is null or regexp_replace(lower(e->>'title'),'[[:space:]:<>]','','g') is distinct from regexp_replace(lower(nm),'[[:space:]:<>]','','g')
     or regexp_replace(lower(ls->2->>'text'),'[[:space:]:<>]','','g') is distinct from regexp_replace(lower(nm),'[[:space:]:<>]','','g')
     or exists(select from jsonb_array_elements(ls) with ordinality x(v,n) where n>1 and (v->>'text') ~ '20[0-9]{2} *[년./-] *[0-9]{1,2}')
     then return false;end if;
   return true;
 elsif a->>'format'='paju_hwp' then
   parts:=regexp_match(nm,'^제([1-9][0-9]*)회 파주시립예술단 정기공연, (.+) \[파주\]$');digest_:=a#>>'{sources,attachment,sha}';
   if parts is null or rawurl !~ '^https://www\.pajucf\.or\.kr/business/02_1_view\.php\?no=[0-9]+(&page=)?$'
     or coalesce(a#>>'{sources,release,url}','') !~ '^https://www\.paju\.go\.kr/user/board/BD_board.view.do\?bbsCd=1023&seq=[0-9]+$'
     or coalesce(a#>>'{sources,attachment,url}','') !~ '^https://www\.paju\.go\.kr/component/file/ND_fileDownload\.do\?id=[a-f0-9-]+$'
     or digest_ is null or a#>>'{notice,source_sha}' is distinct from digest_ or e->'program' is distinct from '[]'::jsonb
     or e->>'title' is distinct from '[대관] 파주시립예술단 제'||parts[1]||'회 정기공연 <'||parts[2]||'>'
     or room[1] is distinct from '파주운정행복센터' or room[2] is distinct from '공연장' or hall is distinct from '운정행복센터 공연장'
     or jsonb_array_length(ls)<>10 or ls->0->>'text' is distinct from '파주시립예술단 제'||parts[1]||'회 정기연주회' or ls->3->>'text' is distinct from parts[2]
     or ls->4->>'text' is distinct from to_char(day,'YYYY"년 "FMMM"월 "FMDD"일"')||'('||ko||') '||clock||' '||hall
     or ls->7->>'text' is distinct from '프로그램' or a#>>'{rows,0,poster_title}' is distinct from parts[2]
     or position('파주시는 '||extract(month from day)::int||'월 '||extract(day from day)::int||'일 '||
       (case when hh>=12 then '오후 ' else '오전 ' end)||(case when hh%12=0 then 12 else hh%12 end)::text||'시 '||mm||'분 운정행복센터 대공연장에서'
       in coalesce(a#>>'{notice,dated}',''))<>1 then return false;end if;
   return true;
 end if;
 return false;
exception when data_exception then return false;
end $$;

create function public.publish_organizer_program(p_id uuid,p_document jsonb,p_expected jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare p public.performances;d jsonb;ptr jsonb;src jsonb;reg jsonb;a jsonb;env jsonb; program jsonb; now_rows jsonb;
 sha text:=p_document->>'sha'; k text:=p_document->>'authority'; poster text;txt text:=p_document->>'envelope_utf8'; hash text; audit text;
 official text; checked timestamptz; against jsonb;
begin
 select * into p from public.performances where id=p_id for update;
 if not found or p.starts_on is null or p.starts_on is distinct from p.ends_on or cardinality(p.intro_image_urls) is distinct from 1
   then return '{"status":"single_date_and_source_required","items":0}';end if;
 poster:=p.intro_image_urls[1];
 if coalesce(sha,'') !~ '^[0-9a-f]{64}$' or coalesce(k,'') !~ '^[a-f0-9]{64}$' or poster is null or txt is null or octet_length(txt) not between 1 and 524288
   then return '{"status":"stale_source","items":0}';end if;
 select payload into d from public.provider_records where provider='kopis' and entity_type='performance_detail' and provider_id=p.kopis_performance_id for share;
 if d->>'mt20id' is distinct from p.kopis_performance_id or d->>'prfnm' is distinct from p.title
   or (d#>'{styurls,styurl}' is distinct from to_jsonb(poster) and d#>'{styurls,styurl}' is distinct from to_jsonb(p.intro_image_urls))
   then return '{"status":"stale_kopis_detail","items":0}';end if;
 select payload into src from public.provider_records where provider='r2' and entity_type='source_archive' and provider_id=encode(sha256(convert_to(poster,'UTF8')),'hex') for share;
 select payload into ptr from public.provider_records where provider='codex_vision' and entity_type='direct_reading' and provider_id=p_document->>'reading_key' for share;
 hash:=encode(sha256(convert_to(txt,'UTF8')),'hex');env:=txt::jsonb;
 if src->>'source_url' is distinct from poster or src->>'bucket' is distinct from 'classic-hubble-sources' or src->>'sha256' is distinct from sha
   or src->>'object_key' is distinct from 'originals/sha256/'||left(sha,2)||'/'||sha or not coalesce(src->'performance_ids' ? p_id::text,false)
   or ptr->>'result_sha256' is distinct from hash or ptr->>'result_object_key' is distinct from 'extractions/sha256/'||left(hash,2)||'/'||hash
   or ptr->>'source_sha256' is distinct from sha or ptr->>'source_object_key' is distinct from src->>'object_key' or ptr->>'bucket' is distinct from src->>'bucket'
   or ptr->>'method' is distinct from 'chat_model_direct_image_reading' or ptr->>'pipeline_version' is distinct from 'codex-direct-vision-v1'
   or env->'method' is distinct from ptr->'method' or env->'pipeline_version' is distinct from ptr->'pipeline_version' or env->'bucket' is distinct from ptr->'bucket'
   or env->'source_object_key' is distinct from ptr->'source_object_key' or env->>'source_sha256' is distinct from sha or env#>>'{reading,source_sha256}' is distinct from sha
   or coalesce(ptr->>'reading_sha256','') !~ '^[a-f0-9]{64}$' or env->'reading_sha256' is distinct from ptr->'reading_sha256'
   or env#>'{reading,coverage}' is distinct from ptr->'coverage' or env#>'{reading,status}' is distinct from ptr->'status'
   then return '{"status":"poster_evidence_changed","items":0}';end if;
 select payload into reg from public.provider_records where provider='organizer_program' and entity_type='source_authority' and provider_id=k for share;
 if reg->>'bucket' is distinct from src->>'bucket' or reg->>'result_object_key' is distinct from 'extractions/sha256/'||left(k,2)||'/'||k
   or reg->>'result_sha256' is distinct from k or octet_length(reg->>'proof_utf8')>100000 or encode(sha256(convert_to(reg->>'proof_utf8','UTF8')),'hex') is distinct from k
   then return '{"status":"missing_official_evidence","items":0}';end if;
 a:=(reg->>'proof_utf8')::jsonb;official:=a->>'public_url';
 if a->>'version' is distinct from 'corroborated-organizer-v1' or a->>'id' is distinct from p_id::text or a->>'kopis' is distinct from p.kopis_performance_id
   or a->>'image_sha' is distinct from sha or a->>'image_url' is distinct from poster or a->>'envelope_sha' is distinct from hash or a->'reading_sha' is distinct from ptr->'reading_sha256'
   or public.organizer_program_event(a,d,env->'reading',p.starts_on) is not true then return '{"status":"official_event_not_verified","items":0}';end if;
 program:=public.organizer_program_items(env->'reading',a);if program is null then return '{"status":"work_identity_not_verified","items":0}';end if;
 if p_expected is not null then
   checked:=(p_document->>'checked_at')::timestamptz;
   select jsonb_object_agg(x,d->x) into against from unnest(array['mt20id','prfnm','prfpdfrom','prfpdto','dtguidance','fcltynm','styurls']) x;
   if checked is null or checked not between now()-interval '5 minutes' and now()+interval '1 minute' or p_expected is distinct from program
     or p_document->>'live_sha' is distinct from sha or p_document->>'content_type' is distinct from src->>'content_type'
     or p_document->'live_event' is distinct from a->'event' or p_document->'live_detail' is distinct from against
     or (a->>'format'='paju_hwp' and p_document->>'live_attachment_sha' is distinct from a#>>'{notice,source_sha}')
     then return '{"status":"live_sources_or_preview_changed","items":0}';end if;
 end if;
 audit:=p_id::text||':'||k;
 perform 1 from public.program_items where performance_id=p_id for update;
 select coalesce(jsonb_agg(jsonb_build_object('position',position,'work_id',work_id,'composer_name',composer_name,'display_title',display_title,
   'performed_scope',performed_scope,'scope_details',scope_details) order by position),'[]') into now_rows from public.program_items where performance_id=p_id;
 if now_rows=program and p.program_status::text='partially_confirmed' and p.program_source_url=official and p.program_image_urls=p.intro_image_urls
   and not exists(select from public.program_items where performance_id=p_id and (source_provider is distinct from 'organizer_program' or source_type::text is distinct from 'official' or source_url is distinct from official))
   and exists(select from public.provider_records where provider='organizer_program' and entity_type='publication' and provider_id=audit)
   then return jsonb_build_object('status','unchanged','items',jsonb_array_length(program));end if;
 if now_rows<>'[]'::jsonb or p.program_status::text is distinct from 'unknown' or p.program_source_url is not null or cardinality(p.program_image_urls)>0
   then return '{"status":"existing_program_preserved","items":0}';end if;
 if p_expected is null then return jsonb_build_object('status','ready','items',jsonb_array_length(program),'program',program);end if;
 insert into public.provider_records(provider,entity_type,provider_id,payload)values('organizer_program','publication',audit,jsonb_build_object(
   'version',a->>'version','performance_id',p_id,'before',now_rows,'before_performance',to_jsonb(p),'after',program,'official',official,'authority',k,
   'source_sha',sha,'envelope_sha',hash,'reading_sha',ptr->>'reading_sha256','date',p.starts_on,'checked_at',checked));
 insert into public.program_items(performance_id,position,work_id,composer_name,display_title,performed_scope,scope_details,source_provider,source_type,source_url)
   select p_id,(v->>'position')::int,(v->>'work_id')::uuid,v->>'composer_name',v->>'display_title','unknown',v->'scope_details','organizer_program','official',official from jsonb_array_elements(program) v;
 update public.performances set program_status='partially_confirmed',program_source_url=official,program_image_urls=p.intro_image_urls,program_source_updated_at=checked where id=p_id;
 return jsonb_build_object('status','published','items',jsonb_array_length(program));
exception when data_exception then return '{"status":"invalid_evidence","items":0}';
end $$;
revoke all on function public.organizer_quote(jsonb,jsonb), public.organizer_program_event(jsonb,jsonb,jsonb,date), public.organizer_program_items(jsonb,jsonb), public.publish_organizer_program(uuid,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.organizer_quote(jsonb,jsonb), public.organizer_program_event(jsonb,jsonb,jsonb,date), public.organizer_program_items(jsonb,jsonb), public.publish_organizer_program(uuid,jsonb,jsonb) to service_role;
notify pgrst,'reload schema';
