-- A directly observed, single-recital programme followed by an annual index.
-- Derive exactly the same proof for the preview and under the publication locks.
create function public.direct_series_program_proof(
  p_utf8 text, p_sha text, p_day date, p_matching jsonb default null
) returns jsonb language plpgsql immutable security invoker set search_path = '' as $$
declare
  d jsonb; ls jsonb; items jsonb; entry jsonb; ref jsonb; fields jsonb; span jsonb;
  n int; i int; j int; k int; v text; role_name text; composer text; target_role text;
  prog int; artist int; cal int; anchor int; m text[]; current_day date; last_day date; date_line int;
  field text; wanted int; quote text;
  role_pattern constant text := '^(피아니스트|바이올리니스트|첼리스트) [가-힣]{2,5}$';
begin
  if p_day is null or p_utf8 is null or octet_length(p_utf8) not between 1 and 131072
    or encode(sha256(convert_to(p_utf8,'UTF8')),'hex') is distinct from p_sha then return null; end if;
  d := p_utf8::jsonb; ls := d->'lines'; items := d->'items';
  if d->>'status' is distinct from 'text_extracted' or d->>'coverage' is distinct from 'complete'
    or d->>'extraction_status' is distinct from 'items_extracted' or jsonb_typeof(ls) is distinct from 'array'
    or jsonb_typeof(items) is distinct from 'array' then return null; end if;
  n := jsonb_array_length(ls); k := jsonb_array_length(items);
  if n not between 20 and 300 or k not between 1 and 30 then return null; end if;
  if p_matching is not null and (jsonb_typeof(p_matching) is distinct from 'array' or jsonb_array_length(p_matching)<>k)
  then return null; end if;
  for i in 0..n-1 loop
    v := btrim(ls->i->>'text');
    if ls->i->'page_index' is distinct from '0'::jsonb or coalesce(v,'')='' then return null; end if;
    if lower(v)='program' then
      if prog is not null then return null; end if; prog := i;
    elsif lower(v)='artist' then
      if artist is not null or prog is null then return null; end if; artist := i;
    elsif v='<위대한 작곡가> 시리즈 연간 공연 일정' then
      if cal is not null or artist is null then return null; end if; cal := i;
    elsif cal is null then
      m := regexp_match(v,'^([0-9]{4})\. *([0-9]{1,2})\. *([0-9]{1,2}) *\(([월화수목금토일])\) ([0-9]{1,2}):([0-9]{2})$');
      if m is not null then
        if date_line is not null or prog is not null or make_date(m[1]::int,m[2]::int,m[3]::int)<>p_day
          or m[4]<>substr('월화수목금토일',extract(isodow from p_day)::int,1)
          or m[5]::int>23 or m[6]::int>59 then return null; end if;
        date_line := i;
      elsif v ~ '^[0-9]{1,4} *[./월] *[0-9]' or v ~ '[0-9] *월 *[0-9]+ *일'
        or v ~* '(예매|예약|티켓|booking|ticket|추가 프로그램|program(me)? [12AB]|다른 공연일)'
      then return null; end if;
    end if;
  end loop;
  if prog is null or artist is null or cal is null or date_line is null or artist-prog<>k+3
    or not (cal+14=n or (cal+13=n))
  then return null; end if;
  -- The footer is solely four dated columns of credits (and an optional publisher).
  if cal+14=n and ls->(n-1)->>'text' <> '금호문화재단' then return null; end if;
  for j in 0..3 loop
    i := cal+1+3*j; m := regexp_match(ls->i->>'text','^([0-9]{1,2}) */ *([0-9]{1,2})$');
    role_name := ls->(i+1)->>'text'; composer := ls->(i+2)->>'text';
    if m is null or role_name !~ role_pattern or composer !~ '^[가-힣A-Za-z.]+( [가-힣A-Za-z.]+){0,4}$'
    then return null; end if;
    current_day := make_date(extract(year from p_day)::int,m[1]::int,m[2]::int);
    if last_day>=current_day then return null; end if;
    last_day := current_day;
    if current_day=p_day then
      anchor := i; target_role := role_name;
      if composer is distinct from ls->(prog+2)->>'text' then return null; end if;
    end if;
  end loop;
  if anchor is null or date_line<1 or ls->(date_line-1)->>'text' !~ ('^'||target_role||'( [IⅡ]+)?$')
    or left(ls->(prog+1)->>'text',length(target_role)+1)<>target_role||'의' then return null; end if;
  for j in 0..k-1 loop
    ref := items->j; entry := p_matching->j;
    if ref->>'context' is distinct from 'program' or ref->>'scope' is distinct from 'full_work'
      or ref->'movements' is distinct from '[]'::jsonb then return null; end if;
    fields := jsonb_build_object('movements','[]'::jsonb);
    foreach field in array array['composer','title','catalogue','key'] loop
      if field='key' and ref->field='null'::jsonb then fields:=fields||jsonb_build_object(field,null); continue; end if;
      if jsonb_typeof(ref->field) is distinct from 'array' or jsonb_array_length(ref->field)<>1 then return null; end if;
      span := ref->field->0; quote := span->>'quote'; wanted := case when field='composer' then prog+2 else prog+3+j end;
      if jsonb_typeof(span->'quote') is distinct from 'string' or coalesce(btrim(quote),'')=''
        or span->>'line_id' is distinct from 'L'||lpad(wanted::text,6,'0')
        or strpos(ls->wanted->>'text',quote)=0
        or (field='composer' and quote is distinct from ls->(anchor+2)->>'text') then return null; end if;
      fields := fields||jsonb_build_object(field,quote);
    end loop;
    if p_matching is not null and (entry->'evidence' is distinct from ref or entry->'fields' is distinct from fields
      or entry->>'context' is distinct from 'program' or entry->>'scope' is distinct from 'full_work')
    then return null; end if;
  end loop;
  return jsonb_build_object('version','direct-series-calendar-v1','performance_date',to_char(p_day,'YYYY-MM-DD'),
    'date_line',date_line,'program_line',prog,'end_line',artist,'calendar_line',cal,'calendar_target_line',anchor);
exception when data_exception then return null;
end $$;
revoke all on function public.direct_series_program_proof(text,text,date,jsonb) from public,anon,authenticated;
grant execute on function public.direct_series_program_proof(text,text,date,jsonb) to service_role;

do $migration$
declare
  sig regprocedure := 'public.publish_direct_vision_program(uuid,jsonb,jsonb,jsonb,jsonb,jsonb)'::regprocedure;
  old text := '  if p_evaluation->>''publication_version'' is distinct from ''direct-vision-single-source-v1''';
  guard text := $guard$  if p_evaluation->>'publication_version'='direct-vision-series-calendar-v1' then
    if jsonb_typeof(p_evaluation->'series_program') is distinct from 'object'
      or jsonb_typeof(p_evaluation->'series_reading_utf8') is distinct from 'string'
      or jsonb_typeof(p_evaluation#>'{matching,items}') is distinct from 'array'
      or p_evaluation->'series_program' is distinct from public.direct_series_program_proof(
        p_evaluation->>'series_reading_utf8',v_reading->>'reading_sha256',v_performance.starts_on,p_evaluation#>'{matching,items}')
    then raise exception 'Invalid annual programme evidence'; end if;
    p_evaluation := p_evaluation - 'series_reading_utf8';
  elsif p_evaluation ? 'series_program' or p_evaluation ? 'series_reading_utf8' then
    raise exception 'Unexpected annual programme evidence';
  end if;
  if coalesce(p_evaluation->>'publication_version','') not in ('direct-vision-single-source-v1','direct-vision-series-calendar-v1')$guard$;
  body text := pg_get_functiondef(sig);
begin
  if strpos(body,guard)>0 then return; end if;
  if length(body)-length(replace(body,old,''))<>length(old) then raise exception 'Unexpected direct publication contract'; end if;
  execute replace(body,old,guard);
end $migration$;
notify pgrst, 'reload schema';
