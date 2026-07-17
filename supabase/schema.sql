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

do $$
begin
  alter publication supabase_realtime add table public.ui_review_issue_state;
exception
  when duplicate_object then null;
end
$$;
