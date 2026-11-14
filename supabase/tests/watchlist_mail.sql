-- Transaction-only test: fixture data and all queued mail are rolled back.
begin;
do $test$
declare
 u uuid := gen_random_uuid(); c uuid := gen_random_uuid(); w uuid := gen_random_uuid();
 w2 uuid := gen_random_uuid(); p uuid := gen_random_uuid(); e uuid;
begin
 insert into auth.users(id,email,email_confirmed_at) values(u,u::text||'@example.invalid',now());
 insert into public.profiles(id) values(u) on conflict do nothing;
 insert into public.composers(id,name) values(c,'mail fixture');
 insert into public.works(id,composer_id,slug,title) values(w,c,w::text,'one'),(w2,c,w2::text,'two');
 insert into public.performances(id,kopis_performance_id,title,starts_at,starts_on)
 values(p,p::text,'fixture',now()+interval '10 days',current_date+10);
 insert into public.watchlist_items(user_id,work_id) values(u,w),(u,w2);
 insert into public.program_items(performance_id,work_id,display_title,source_type,position)
 values(p,w,'one','estimated',1);
 if exists(select from watchmail.outbox where user_id=u) then raise exception 'unverified sent'; end if;
 update public.program_items set source_type='official' where performance_id=p;
 delete from public.program_items where performance_id=p;
 insert into public.program_items(performance_id,work_id,display_title,source_type,position)
 values(p,w,'one','official',1),(p,w2,'two','verified',2);
 if (select count(*) from watchmail.outbox where user_id=u)<>1 then raise exception 'not one event'; end if;
 select id into e from watchmail.outbox where user_id=u;
 insert into public.notification_preferences(user_id,channel,enabled) values(u,'email',false)
 on conflict(user_id,channel) do update set enabled=false;
 if exists(select from public.claim_watchlist_email(e)) then raise exception 'opt out ignored'; end if;
 update public.notification_preferences set enabled=true where user_id=u and channel='email';
 if (select count(*) from public.claim_watchlist_email(e))<>1 then raise exception 'missing claim'; end if;
 if exists(select from public.claim_watchlist_email(e)) then raise exception 'overlapping claim'; end if;
 update watchmail.outbox set lease_until=now()-interval '1 second' where id=e;
 if (select event_id from public.claim_watchlist_email(e)) is distinct from e then raise exception 'unstable retry key'; end if;
 update watchmail.outbox set lease_until=now()-interval '1 second', first_attempt=now()-interval '25 hours' where id=e;
 if exists(select from public.claim_watchlist_email(e)) then raise exception 'unsafe retry after provider expiry'; end if;
 perform public.finish_watchlist_email(e,'fixture');
 if exists(select from public.claim_watchlist_email(e)) then raise exception 'repeat delivery'; end if;
 if has_function_privilege('anon','public.claim_watchlist_email(uuid)','execute') then raise exception 'exposed queue'; end if;
 begin
  perform public.watchlist_mail_worker('bad-token','claim',e);
  raise exception 'bad token allowed';
 exception when insufficient_privilege then null;
 end;
end $test$;
rollback;
