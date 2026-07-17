create table if not exists public.ui_review_issue_state (
  report_id text not null,
  issue_id text not null,
  status text not null check (
    status in ('待处理', '待代码确认', '处理中', '已修复', '忽略')
  ),
  note text not null default '',
  updated_at timestamptz not null default now(),
  updated_by uuid,
  primary key (report_id, issue_id)
);

alter table public.ui_review_issue_state enable row level security;

grant usage on schema public to anon, authenticated;
revoke all on public.ui_review_issue_state from anon, authenticated;
grant select on public.ui_review_issue_state to anon, authenticated;
grant insert, update on public.ui_review_issue_state to authenticated;

drop policy if exists "Public can read review state" on public.ui_review_issue_state;
create policy "Public can read review state"
on public.ui_review_issue_state
for select
to anon, authenticated
using (true);

drop policy if exists "Authenticated collaborators can insert review state" on public.ui_review_issue_state;
create policy "Authenticated collaborators can insert review state"
on public.ui_review_issue_state
for insert
to authenticated
with check (true);

drop policy if exists "Authenticated collaborators can update review state" on public.ui_review_issue_state;
create policy "Authenticated collaborators can update review state"
on public.ui_review_issue_state
for update
to authenticated
using (true)
with check (true);

create or replace function public.stamp_ui_review_issue_state()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  new.updated_at = now();
  new.updated_by = auth.uid();
  return new;
end;
$$;

drop trigger if exists ui_review_issue_state_stamp on public.ui_review_issue_state;
create trigger ui_review_issue_state_stamp
before insert or update on public.ui_review_issue_state
for each row execute function public.stamp_ui_review_issue_state();

insert into public.ui_review_issue_state (report_id, issue_id, status, note)
select
  'flash-purchase-store-ui-review-v1',
  issue_id,
  case
    when issue_id in (
      'UI-01', 'UI-05', 'UI-09', 'UI-10', 'UI-11',
      'UI-12', 'UI-13', 'UI-14', 'UI-15', 'UI-16'
    ) then '忽略'
    when issue_id = 'UI-18' then '待代码确认'
    else '待处理'
  end,
  ''
from unnest(array[
  'UI-01', 'UI-02', 'UI-03', 'UI-04', 'UI-05',
  'UI-06', 'UI-07', 'UI-08', 'UI-09', 'UI-10',
  'UI-11', 'UI-12', 'UI-13', 'UI-14', 'UI-15',
  'UI-16', 'UI-17', 'UI-18', 'UI-19'
]) as issue_id
on conflict (report_id, issue_id) do nothing;

do $$
begin
  alter publication supabase_realtime add table public.ui_review_issue_state;
exception
  when duplicate_object then null;
end
$$;
