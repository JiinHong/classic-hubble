-- One interpretation of the layout for both previews and the locked publication.
-- The bytes are transient; the immutable OCR pointer and original line numbers
-- suffice to reproduce the proof later. No new public evidence tables.
create function public.paddle_dated_program_section(
  p_ocr_utf8 text, p_sha text, p_day date, p_entries jsonb default '[]'
) returns jsonb language plpgsql immutable security invoker set search_path = '' as $$
declare
  d jsonb; lines jsonb; n integer; i integer; s text; line jsonb; box jsonb;
  program integer; closing integer; anchor integer; first_day date; day_value date;
  heads integer[] := '{}'; m text[]; yr integer := extract(year from p_day);
  good boolean; center_x numeric; image_h numeric; last_top numeric := -1; section_bottom numeric := -1;
  max_bottom numeric := -1; x1 numeric; y1 numeric; x2 numeric; y2 numeric;
  lo integer; hi integer; entry jsonb; ref jsonb; spans jsonb; q jsonb;
  line_id text; field text; cited integer; groups jsonb; rendered jsonb; parts text[];
  ticket_pattern constant text := '예매|티켓|판매|접수|신청|매표|예약|마감|오픈|ticket|booking|reservation|on sale';
  month_name constant text := '(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(t(ember)?)?|oct(ober)?|nov(ember)?|dec(ember)?)';
begin
  if p_day is null or p_sha is null or p_ocr_utf8 is null
    or octet_length(p_ocr_utf8) not between 1 and 524288
    or encode(sha256(convert_to(p_ocr_utf8,'UTF8')),'hex') is distinct from p_sha
    or jsonb_typeof(p_entries) is distinct from 'array' or jsonb_array_length(p_entries)>400
  then return null; end if;
  d := p_ocr_utf8::jsonb; lines := d->'lines';
  if d->>'status' is distinct from 'text_extracted' or d->>'coordinate_space' is distinct from 'exif_oriented_pixels'
    or jsonb_typeof(lines) is distinct from 'array'
    or jsonb_typeof(d->'width') is distinct from 'number' or jsonb_typeof(d->'height') is distinct from 'number'
  then return null; end if;
  n := jsonb_array_length(lines); center_x := (d->>'width')::numeric / 2; image_h := (d->>'height')::numeric;
  if n not between 7 and 1500 or center_x <= 0 or image_h <= 0 then return null; end if;
  for i in 0..n-1 loop
    line := lines->i; s := lower(btrim(line->>'text'));
    if coalesce(line->>'page_index','0') <> '0' or coalesce(s,'')='' then return null; end if;
    good := jsonb_typeof(line->'score')='number' and (line->>'score')::numeric between 0.9 and 1;
    if s in ('program','programme','프로그램') then
      if program is not null or good is not true then return null; end if;
      program := i;
    elsif program is null or closing is not null then
      continue;
    end if;
    -- V1 is limited to a single vertical column. Do not assume reading order
    -- for side-by-side programmes, another page, or rows crossing a date.
    box := line->'bbox';
    if jsonb_typeof(box) is distinct from 'array' or jsonb_array_length(box) <> 4
      or exists(select 1 from jsonb_array_elements(box) v where jsonb_typeof(v)<>'number')
    then return null; end if;
    x1 := (box->>0)::numeric; y1 := (box->>1)::numeric; x2 := (box->>2)::numeric; y2 := (box->>3)::numeric;
    if not (0<=x1 and x1<center_x and center_x<x2 and x2<=2*center_x
      and 0<=y1 and last_top<=y1 and section_bottom<=y1 and y1<y2 and y2<=image_h)
    then return null; end if;
    last_top := y1;
    if i=program then section_bottom := y2;
    elsif s in ('artist','artists','연주자 소개','profile','arlist') then
      if cardinality(heads)<>2 or good is not true or y1<max_bottom
        or (s='arlist' and not coalesce((lines->(i+1)->>'text') ~ '^©[^[:space:]]'
          and jsonb_typeof(lines->(i+1)->'score')='number'
          and (lines->(i+1)->>'score')::numeric between 0.9 and 1,false))
      then return null; end if;
      closing := i;
    else
      m := regexp_match(s,'^([0-9]{1,2}) *월 *([0-9]{1,2}) *일 *\(([월화수목금토일])\)$');
      if m is not null then
        day_value := make_date(yr,m[1]::integer,m[2]::integer);
        if good is not true or y1<max_bottom or m[3]<>substr('월화수목금토일',extract(isodow from day_value)::integer,1)
          or (cardinality(heads)=0 and i<>program+1)
          or (cardinality(heads)=1 and (i<=heads[1]+1 or day_value<>first_day+1))
          or cardinality(heads)>=2
        then return null; end if;
        if cardinality(heads)=0 then first_day := day_value; end if;
        heads := array_append(heads,i); section_bottom := y2;
      elsif cardinality(heads)=0 or s ~* ticket_pattern
        or s ~* ('(^|[^a-z])'||month_name||'[., ]+[0-9]|[0-9]+[., ]+'||month_name||'([^a-z]|$)')
        or s ~ '[0-9] *일 *[(\[]|^[0-9]{1,2} *[(\[][월화수목금토일]'
        or s ~* '(profile|artist|biograph|history|performer|program(me)? note|출연|약력|연주자|프로필|프로그램|공연 *안내|해설|이력|다른 *공연|[0-9] *월 *[0-9]|^[^[:alnum:]]*[0-9]+ *[./년월-] *[0-9])'
      then return null;
      end if;
    end if;
    max_bottom := greatest(max_bottom,y2);
  end loop;
  if closing is null or closing<=heads[2]+1 or p_day not in (first_day,first_day+1) then return null; end if;
  -- A weekday alone repeats across years. Require an explicit, reliable cover
  -- date agreeing with the first section; a sale date cannot supply its year.
  for i in 0..program-1 loop
    line := lines->i; s := btrim(line->>'text');
    m := regexp_match(s,'^(20[0-9]{2}) *[.,] *([0-9]{1,2}) *[.] *([0-9]{1,2}) *(\[([월화수목금토일])\]|\(([월화수목금토일])\))$');
    if m is null then
      if s ~ '^20[0-9]{2} *[.,년/-] *[0-9]' then return null; end if;
      continue;
    end if;
    if i>0 and (lines->(i-1)->>'text') ~* ticket_pattern then return null; end if;
    day_value := make_date(m[1]::integer,m[2]::integer,m[3]::integer);
    if day_value not in (first_day,first_day+1)
      or coalesce(m[5],m[6])<>substr('월화수목금토일',extract(isodow from day_value)::integer,1)
    then return null; end if;
    if day_value=first_day and anchor is null and jsonb_typeof(line->'score')='number'
      and (line->>'score')::numeric between 0.9 and 1 then anchor := i; end if;
  end loop;
  if anchor is null then return null; end if;
  lo := case when p_day=first_day then heads[1] else heads[2] end;
  hi := case when p_day=first_day then heads[2] else closing end;
  for entry in select value from jsonb_array_elements(p_entries) loop
    if jsonb_typeof(entry->'publication_eligible') is distinct from 'boolean' then return null; end if;
    if entry->'publication_eligible'='false'::jsonb then continue; end if;
    ref := entry->'evidence';
    if jsonb_typeof(ref->'composer') is distinct from 'array' or jsonb_array_length(ref->'composer')<1
      or jsonb_typeof(ref->'title') is distinct from 'array' or jsonb_array_length(ref->'title')<1
      or jsonb_typeof(ref->'movements') is distinct from 'array'
    then return null; end if;
    foreach field in array array['composer','title','catalogue','key','movements'] loop
      if field in ('key','catalogue') and ref->field='null'::jsonb then
        if entry->'fields'->field is distinct from 'null'::jsonb then return null; end if;
        continue;
      end if;
      groups := case when field='movements' then ref->field else jsonb_build_array(ref->field) end;
      rendered := '[]';
      for spans in select value from jsonb_array_elements(groups) loop
        if jsonb_typeof(spans) is distinct from 'array' or jsonb_array_length(spans)=0 then return null; end if;
        parts := '{}';
        for q in select value from jsonb_array_elements(spans) loop
          line_id := q->>'line_id';
          if line_id is null or line_id !~ '^L[0-9]{6}$' then return null; end if;
          cited := substring(line_id from 2)::integer;
          line := lines->cited;
          if cited<=lo or cited>=hi or jsonb_typeof(q->'quote') is distinct from 'string'
            or btrim(q->>'quote')='' or strpos(line->>'text',q->>'quote')=0
            or jsonb_typeof(line->'score') is distinct from 'number' or (line->>'score')::numeric not between 0.9 and 1
          then return null; end if;
          if not ((q->>'quote')=any(parts)) then parts := array_append(parts,q->>'quote'); end if;
        end loop;
        rendered := rendered || jsonb_build_array(array_to_string(parts,' '));
      end loop;
      if (case when field='movements' then rendered else rendered->0 end)
        is distinct from entry->'fields'->field then return null; end if;
    end loop;
  end loop;
  return jsonb_build_object('version','dated-program-section-v1','performance_date',to_char(p_day,'YYYY-MM-DD'),
    'program_line',program,'anchor_line',anchor,'heading_line',lo,'end_line',hi);
exception when data_exception then return null;
end;
$$;
revoke all on function public.paddle_dated_program_section(text,text,date,jsonb) from public,anon,authenticated;
grant execute on function public.paddle_dated_program_section(text,text,date,jsonb) to service_role;

-- Keep the legacy public transaction and its grants. Insert the additional
-- contract only after it has locked/reloaded the archive, OCR and review.
do $migration$
declare
  signature constant regprocedure := 'public.publish_paddle_program_bundle(uuid,jsonb,jsonb,jsonb,jsonb)'::regprocedure;
  old_guard constant text := '    if coalesce(doc->>''date_binding'','''') not in (''target'',''absent'')';
  old_date constant text := 'has_date := has_date or doc->>''date_binding''=''target'';';
  old_title constant text := $title$concat_ws(' ',nullif(entry#>>'{fields,title}',''),nullif(entry#>>'{fields,catalogue}',''))$title$;
  section_title constant text := $title$case when doc->>'date_binding'='dated_section'
        and jsonb_typeof(reference->'catalogue')='array' and not exists(
          select from jsonb_array_elements(reference->'catalogue') c where not exists(
            select from jsonb_array_elements(reference->'title') t where t->>'line_id'=c->>'line_id'
              and strpos(t->>'quote',c->>'quote')>0))
        then entry#>>'{fields,title}' else $title$;
  definition text := pg_get_functiondef(signature);
  new_guard constant text := $guard$    if doc->>'date_binding'='dated_section' then
      if jsonb_array_length(p_documents)<>1 or not (doc ? 'program_section')
        or jsonb_typeof(doc->'program_section') is distinct from 'object'
        or jsonb_typeof(p_evaluation->'section_ocr_utf8') is distinct from 'string'
        or doc->'program_section' is distinct from public.paddle_dated_program_section(
          p_evaluation->>'section_ocr_utf8',oc->>'result_sha256',perf.starts_on,doc#>'{matching,items}')
      then raise exception 'Invalid date section proof'; end if;
      p_evaluation := p_evaluation - 'section_ocr_utf8';
    elsif doc ? 'program_section' or p_evaluation ? 'section_ocr_utf8' then
      raise exception 'Unexpected date section proof';
    end if;
    if coalesce(doc->>'date_binding','') not in ('target','absent','dated_section')$guard$;
begin
  if strpos(definition,new_guard)>0 then return; end if;
  if length(definition)-length(replace(definition,old_guard,''))<>length(old_guard)
    or length(definition)-length(replace(definition,old_date,''))<>length(old_date)
    or length(definition)-length(replace(definition,old_title,''))<>length(old_title)
  then raise exception 'Unexpected bundle implementation; inspect before migration'; end if;
  definition := replace(definition,old_title,section_title||old_title||' end');
  execute replace(replace(definition,old_guard,new_guard),old_date,
    'has_date := has_date or doc->>''date_binding'' in (''target'',''dated_section'');');
end;
$migration$;
notify pgrst,'reload schema';
