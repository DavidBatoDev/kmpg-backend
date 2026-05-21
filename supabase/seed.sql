-- Demo student for local testing and hackathon rehearsal
insert into public.students (
  copilot_user_id,
  name,
  email,
  timezone,
  preferred_study_style,
  preferred_study_times,
  metadata
)
values (
  'demo-user-1',
  'Demo Student',
  'demo@example.com',
  'Asia/Manila',
  'short focused blocks',
  '[{"day":"weekday","start":"19:00","end":"22:00"}]'::jsonb,
  '{"max_study_hours_per_day": 3}'::jsonb
)
on conflict (copilot_user_id) do nothing;
