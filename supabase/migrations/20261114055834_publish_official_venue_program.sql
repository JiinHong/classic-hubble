-- Publish a bounded set of composer/title/catalogue matches. Never replace another authority.
create function public.publish_official_venue_program(p_id uuid, doc jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
 p public.performances%rowtype;
 provider_key text := doc->>'provider';
 u text := doc->>'url';
 src text := doc->>'source';
 row_data jsonb;
 fingerprint text := encode(sha256(convert_to(doc::text,'UTF8')),'hex');
 n int;
begin
 if (doc->>'version'='official-program-v1' and jsonb_typeof(doc->'items')='array'
    and jsonb_typeof(doc->'program')='array' and octet_length(doc::text)<=100000
    and jsonb_array_length(doc->'items') between 1 and 60
    and case provider_key
     when 'sac' then u ~ '^https://www\.sac\.or\.kr/site/main/show/show_view\?SN=[0-9]+$' and src=u
     when 'sejong' then u ~ '^https://www\.sejongpac\.or\.kr/portal/performance/performance/performTicket\.do\?performIdx=[0-9]+&menuNo=200320$' and src=u
     when 'bucheon' then u ~ '^https://www\.bucheonphil\.or\.kr/front/M0000012/event/view\.do\?eventId=EV[0-9]+$'
       and src ~ '^https://www\.bucheonphil\.or\.kr/front/M0000133/article/view\.do\?atcId=AT[0-9]+$'
     when 'seoulphil' then u ~ '^https://www\.seoulphil\.or\.kr/perf/view\?perfNo=[0-9]+$' and src=u
     else false end) is not true then raise exception 'Invalid official program evidence'; end if;
 select * into strict p from public.performances where id=p_id for update;
 if (p.kopis_performance_id=doc->>'kopis' and p.title=doc->>'kopis_title' and p.starts_on=p.ends_on
     and p.starts_on::text=doc->>'day' and p.venue_id::text=doc->>'venue'
     and p.venue_hall_id::text=doc->>'hall' and p.schedule_text=doc->>'schedule'
     and p.starts_on >= (current_timestamp at time zone 'Asia/Seoul')::date
     and position((doc->>'clock') in p.schedule_text)>0 and length(doc->>'official_title')>0
     and exists(select from public.venue_halls h where h.id=p.venue_hall_id and h.venue_id=p.venue_id))
    is not true then return '{"status":"stale_event","items":0}'; end if;
 n:=jsonb_array_length(doc->'items');
 if (select count(distinct v->>'work_id') from jsonb_array_elements(doc->'items') v)<>n or
    (select count(distinct (v->>'position')::int) from jsonb_array_elements(doc->'items') v)<>n
 then raise exception 'Duplicate program item'; end if;
 for row_data in select value from jsonb_array_elements(doc->'items') loop
   if ((row_data->>'position')::int between 1 and jsonb_array_length(doc->'program')
     and doc->'program'->((row_data->>'position')::int-1)=jsonb_build_array(row_data->>'credit',row_data->>'title')
     and length(row_data->>'credit')>0 and length(row_data->>'title')>0
     and exists(select from public.works w where w.id=(row_data->>'work_id')::uuid
        and w.composer_id::text=row_data->>'composer_id' and w.catalogue=row_data->>'catalogue'))
     is not true then raise exception 'Unverified or changed work reference'; end if;
 end loop;
 perform 1 from public.program_items where performance_id=p_id for update;
 if exists(select from public.provider_records where provider=provider_key and entity_type='venue_program_v1'
     and provider_id=p_id::text||':'||fingerprint)
    and (select count(*) from public.program_items i join jsonb_array_elements(doc->'items') j
         on i.work_id::text=j->>'work_id' and i.position=(j->>'position')::int
         where i.performance_id=p_id and i.source_url=src and i.source_provider=provider_key)=n
 then return '{"status":"unchanged","items":0}'; end if;
 if p.program_status::text<>'unknown' or p.program_source_url is not null or cardinality(p.program_image_urls)>0
    or exists(select from public.program_items where performance_id=p_id)
 then return '{"status":"existing_program_preserved","items":0}'; end if;
 insert into public.provider_records(provider,entity_type,provider_id,payload)
 values(provider_key,'venue_program_v1',p_id::text||':'||fingerprint,doc);
 insert into public.program_items(performance_id,position,work_id,display_title,composer_name,source_type,
    source_provider,source_url,performed_scope,scope_details)
 select p_id,(j->>'position')::int,(j->>'work_id')::uuid,j->>'title',j->>'credit','official',
    provider_key,src,'unknown',jsonb_build_object('official_event_url',u,'performance_date',doc->>'day')
 from jsonb_array_elements(doc->'items') j;
 update public.performances set program_status='partially_confirmed',program_source_url=src,program_source_updated_at=now() where id=p_id;
 return jsonb_build_object('status','published','items',n);
end $$;
revoke all on function public.publish_official_venue_program(uuid,jsonb) from public,anon,authenticated;
grant execute on function public.publish_official_venue_program(uuid,jsonb) to service_role;
notify pgrst,'reload schema';
