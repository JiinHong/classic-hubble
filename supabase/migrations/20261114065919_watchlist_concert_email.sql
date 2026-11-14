-- Keep the durable deduplication key outside exposed schemas.
create schema watchmail;
revoke all on schema watchmail from public, anon, authenticated;
create table watchmail.links (
 performance_id uuid references public.performances on delete cascade,
 work_id uuid references public.works on delete cascade,
 primary key (performance_id,work_id)
);
create table watchmail.outbox (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users on delete cascade,
 performance_id uuid not null references public.performances on delete cascade,
 created_at timestamptz not null default now(),
 first_attempt timestamptz, lease_until timestamptz, accepted_at timestamptz,
 provider_id text, recipient text, subject_line text, body text, message_work uuid,
 unique(user_id,performance_id)
);
create index on watchmail.outbox(created_at) where accepted_at is null;
create index if not exists watchlist_items_work_user_idx on public.watchlist_items(work_id,user_id);

create function watchmail.trusted(i public.program_items) returns boolean
language sql immutable set search_path='' as $$
 select i.work_id is not null and (i.source_type in ('official','verified')
  or (i.source_type='ocr' and i.source_provider in ('codex_vision','paddleocr') and i.source_url is not null))
$$;
-- Separate enqueue from observing a link so operators can replay one verified
-- relationship for one consenting account without rewriting the public program.
create function watchmail.enqueue(p uuid,w uuid,only_user uuid default null) returns void
language sql set search_path='' as $$
 insert into watchmail.outbox(user_id,performance_id)
 select wi.user_id,p from public.watchlist_items wi
 join public.performances perf on perf.id=p
 where wi.work_id=w and (only_user is null or wi.user_id=only_user)
 and perf.status<>'closed' and perf.kopis_performance_id is not null
 and coalesce(perf.starts_on,(perf.starts_at at time zone 'Asia/Seoul')::date)>=(now() at time zone 'Asia/Seoul')::date
 and exists(select from public.program_items i where i.performance_id=p and i.work_id=w and watchmail.trusted(i))
 and not exists(select from public.notification_preferences pref where pref.user_id=wi.user_id and pref.channel='email' and not pref.enabled)
 on conflict(user_id,performance_id) do nothing
$$;
create function watchmail.observe() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if watchmail.trusted(new) then
  insert into watchmail.links values(new.performance_id,new.work_id) on conflict do nothing;
  if found then perform watchmail.enqueue(new.performance_id,new.work_id); end if;
 end if;
 return null;
end $$;
-- Trigger installation and baseline share the migration transaction and lock.
lock table public.program_items in share row exclusive mode;
insert into watchmail.links select distinct i.performance_id,i.work_id
 from public.program_items i where watchmail.trusted(i);
create trigger watchlist_new_program after insert or update of performance_id,work_id,source_type,source_provider,source_url
 on public.program_items for each row execute function watchmail.observe();

create function public.claim_watchlist_email(only_event uuid default null)
returns table(event_id uuid,recipient text,subject_line text,body text)
language sql security definer set search_path='' as $$
 with candidate as (
  select q.id, u.email as addr, p.title, p.kopis_performance_id as kopis,
   coalesce(p.starts_on,(p.starts_at at time zone 'Asia/Seoul')::date) as day, matched.label, matched.work_id
  from watchmail.outbox q join auth.users u on u.id=q.user_id
  join public.performances p on p.id=q.performance_id
  cross join lateral (select coalesce(w.title_ko,w.title) as label, w.id as work_id from public.program_items i
    join public.watchlist_items wi on wi.user_id=q.user_id and wi.work_id=i.work_id and wi.created_at<=q.created_at
    join public.works w on w.id=i.work_id where i.performance_id=p.id and watchmail.trusted(i)
    and (q.message_work is null or q.message_work=w.id)
    order by i.position,w.id limit 1) matched
  where (only_event is null or q.id=only_event) and q.accepted_at is null
   and u.email_confirmed_at is not null and u.email<>'' and (q.recipient is null or q.recipient=u.email)
   and (q.lease_until is null or q.lease_until<now())
   and (q.first_attempt is null or q.first_attempt>now()-interval '23 hours')
   and not exists(select from public.notification_preferences pref where pref.user_id=u.id and pref.channel='email' and not pref.enabled)
   and p.status<>'closed' and p.kopis_performance_id is not null
   and coalesce(p.starts_on,(p.starts_at at time zone 'Asia/Seoul')::date)>=(now() at time zone 'Asia/Seoul')::date
  order by q.created_at,q.id limit 1 for update of q skip locked
 )
 update watchmail.outbox q set first_attempt=coalesce(q.first_attempt,now()),lease_until=now()+interval '3 minutes',
  recipient=c.addr,message_work=c.work_id,subject_line=coalesce(q.subject_line,'[클래식허블] 관심곡 공연: '||c.title),
  body=coalesce(q.body,format(E'관심곡을 들을 수 있는 공연이 있습니다.\n\n관심곡: %s\n공연: %s\n공연일: %s\nhttps://classichubble.com/performances/%s\n\n관심곡 관리 및 알림 해제: https://classichubble.com/watchlist',c.label,c.title,c.day,c.kopis))
 from candidate c where q.id=c.id returning q.id,q.recipient,q.subject_line,q.body
$$;
create function public.finish_watchlist_email(event uuid,provider text) returns boolean
language sql security definer set search_path='' as $$
 with done as (update watchmail.outbox set accepted_at=coalesce(accepted_at,now()),provider_id=provider
  where id=event and first_attempt is not null and length(provider)>0 and (provider_id is null or provider_id=provider)
  returning id) select exists(select from done)
$$;
revoke all on all functions in schema watchmail from public,anon,authenticated;
revoke all on function public.claim_watchlist_email(uuid),public.finish_watchlist_email(uuid,text) from public,anon,authenticated;
grant execute on function public.claim_watchlist_email(uuid),public.finish_watchlist_email(uuid,text) to service_role;
-- Vercel gets a mail-only capability, never a Supabase service-role key.
create table watchmail.worker_key (singleton boolean primary key check(singleton), digest bytea not null);
create function public.watchlist_mail_worker(token text, operation text, event uuid default null, provider text default null)
returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if not exists(select from watchmail.worker_key k where k.digest=sha256(convert_to(token,'UTF8'))) then
  raise exception 'Unauthorized' using errcode='42501';
 end if;
 if operation='claim' then return (select to_jsonb(r) from public.claim_watchlist_email(event) r);
 elsif operation='finish' and event is not null then return to_jsonb(public.finish_watchlist_email(event,provider));
 else raise exception 'Unknown operation'; end if;
end $$;
revoke all on function public.watchlist_mail_worker(text,text,uuid,text) from public,authenticated;
grant execute on function public.watchlist_mail_worker(text,text,uuid,text) to anon;
notify pgrst,'reload schema';
