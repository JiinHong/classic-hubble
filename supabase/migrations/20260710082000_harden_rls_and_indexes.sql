create index works_composer_id_idx on public.works (composer_id);
create index watchlist_work_id_idx on public.watchlist_items (work_id);
create index push_subscriptions_user_id_idx on public.push_subscriptions (user_id);
create index poster_review_performance_id_idx on public.poster_review_items (performance_id);
create index poster_review_suggested_work_id_idx on public.poster_review_items (suggested_work_id);
create index poster_review_reviewer_id_idx on public.poster_review_items (reviewer_id);
create index notification_deliveries_user_id_idx on public.notification_deliveries (user_id);
create index notification_deliveries_performance_id_idx on public.notification_deliveries (performance_id);
create index notification_deliveries_work_id_idx on public.notification_deliveries (work_id);

create policy "poster review items are service-role managed"
  on public.poster_review_items for all
  using (false)
  with check (false);

create policy "ingestion runs are service-role managed"
  on public.ingestion_runs for all
  using (false)
  with check (false);

drop policy "profiles are self-readable" on public.profiles;
drop policy "profiles are self-insertable" on public.profiles;
drop policy "profiles are self-updatable" on public.profiles;
drop policy "watchlist owner access" on public.watchlist_items;
drop policy "notification preference owner access" on public.notification_preferences;
drop policy "push subscription owner access" on public.push_subscriptions;
drop policy "delivery owner read" on public.notification_deliveries;

create policy "profiles are self-readable"
  on public.profiles for select
  using ((select auth.uid()) = id);

create policy "profiles are self-insertable"
  on public.profiles for insert
  with check ((select auth.uid()) = id);

create policy "profiles are self-updatable"
  on public.profiles for update
  using ((select auth.uid()) = id);

create policy "watchlist owner access"
  on public.watchlist_items for all
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "notification preference owner access"
  on public.notification_preferences for all
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "push subscription owner access"
  on public.push_subscriptions for all
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "delivery owner read"
  on public.notification_deliveries for select
  using ((select auth.uid()) = user_id);

do $$
begin
  if exists (
    select 1
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'rls_auto_enable'
      and pg_get_function_identity_arguments(p.oid) = ''
  ) then
    revoke execute on function public.rls_auto_enable() from anon, authenticated;
  end if;
end $$;
