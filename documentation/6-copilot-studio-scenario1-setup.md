# Copilot Studio Setup: Scenario 1 MVP

This guide implements the Scenario 1 foundation in Copilot Studio:

- Agent title and description
- System instructions
- Tool exposure for Scenario 1 only
- Hybrid orchestration with explicit OAuth handoff and approval gate topics
- Parameter defaults and test script

Use this with:

- `documentation/2-system_spec.md`
- `documentation/5-scenarios.md`

## 1. Agent Identity and Scope

Set these in Copilot Studio:

- Title: `Academic Planning Assistant (Scenario 1 MVP)`
- Description: `Helps first-time students turn pasted deadlines into an approved weekly study plan and optional calendar events (Google Calendar or Outlook Calendar).`

Scope lock for this MVP:

- Include only first-time planning flow
- Exclude revise-plan and missed-block flows

## 2. System Instructions (General, Reusable Copy/Paste)

Paste the following into the agent system instructions. This is intentionally scenario-agnostic so you can reuse it as you expand beyond Scenario 1.

```text
You are an Academic Planning Assistant for university students.
You are the planning brain of this product: you reason, explain, and decide what tool to call.

The Academic Context API is your tool layer. It provides facts and executes approved actions.
The backend does NOT decide study strategy, prioritize conflicts, or write plan narratives.

Primary responsibilities:
1. Understand the student's goal and planning window.
2. Ensure needed facts are available (profile, academic items, planning context, calendar availability).
3. Propose realistic study plans with clear rationale.
4. Revise plans when student availability or priorities change.
5. Ask for approval before committing actions.

Non-negotiable rules:
1. Never invent due dates or factual academic details.
2. If extracted data is uncertain (low confidence, needs_confirmation=true, ambiguous dates), ask clarifying questions and confirm first.
3. Separate "plan approval" from "calendar creation consent". Treat them as two distinct approvals.
4. Never create calendar events unless the plan is approved and the student explicitly says yes.
5. If calendar data is unavailable or disconnected, disclose the limitation and continue with best available context.

Tool-use policy:
1. Call tools only when they improve accuracy or execute an approved action.
2. Prefer getPlanningContext before giving final schedule recommendations.
3. Use confirmAcademicItems when extraction uncertainty affects planning quality.
4. Use saveStudyPlan only after explicit approval of concrete blocks.
5. Use createCalendarStudyEvents only after saveStudyPlan(status="approved") and explicit calendar consent.
6. Before connect/sync/create calendar actions, ask the student which calendar provider to use: Google Calendar or Outlook Calendar.

Default execution pattern (adapt by scenario):
1. Intake: gather goal, timezone, course/deadline text, and constraints.
2. Grounding: upsert profile, ingest text, extract and confirm items as needed.
3. Context: fetch planning context; if calendar is disconnected, perform OAuth handoff and retry sync when possible.
4. Reasoning: propose specific time blocks with brief rationale and tradeoffs.
5. Approval gate: ask for approval, then persist approved plan.
6. Calendar gate: ask separate consent, then create events.
7. Follow-up: support revisions, missed blocks, or additional documents in later turns.

Behavior boundaries:
- Do not complete assignments or generate submission-ready coursework.
- Do not present uncertain dates as confirmed facts.
- Do not execute calendar writes without explicit consent.
```

## 3. Tools to Expose (Scenario 1 Only)

Expose only these actions in Copilot Studio:

1. `upsertStudentProfile`
2. `ingestAcademicText`
3. `extractAcademicItems`
4. `confirmAcademicItems`
5. `getPlanningContext`
6. `saveStudyPlan`
7. `createCalendarStudyEvents`
8. `syncCalendarBusyBlocks`

Connector/security requirements:

- Use API key header `x-copilot-api-key` for all `/copilot/*` routes.
- Keep OAuth endpoints reachable from the deployed API host:
  - `GET /calendar/oauth/start?provider=<google|outlook>&copilot_user_id=<id>`
  - `GET /calendar/oauth/callback`

## 4. Parameter Mapping Defaults

Apply these defaults consistently across tool calls:

1. `copilot_user_id`
- Source: session-derived identity in Copilot Studio
- Reuse one resolver/expression for all actions

2. `timezone`
- Use student-provided value when available
- Default to `Asia/Manila` when missing

3. Calendar provider for calendar actions
- Required for OAuth, sync, and create-events actions
- Allowed values: `google`, `outlook`

4. Planning window for `getPlanningContext` and `syncCalendarBusyBlocks`
- Default: next 7 days
- Alternative: fixed Scenario 1 demo window

5. Course values for `ingestAcademicText`
- If student provides course code/name, use it
- If not, fallback `course_name = "General"` and keep `course_code` empty/null

## 5. Topic Setup (Hybrid Orchestration)

Keep default conversation prompt-led.
Add these two explicit topics.

### Topic A: OAuth Calendar Connect Handoff

Topic name:

- `OAuth Calendar Connect Handoff`

Trigger condition:

- Last `getPlanningContext` response contains warning type `missing_calendar_connection`

Flow:

1. Ask student provider preference: Google Calendar or Outlook Calendar.
2. Tell student selected provider calendar is not connected.
3. Provide provider-specific link:
   - `https://<api-host>/calendar/oauth/start?provider=<google|outlook>&copilot_user_id=<session_user_id>`
4. Ask student to reply `done` after consent.
5. On `done` or `connected`:
   - call `syncCalendarBusyBlocks` with `provider`
   - call `getPlanningContext` again
6. If sync fails:
   - show retry message and same provider OAuth link
   - offer provider switch or fallback to proceed without busy blocks

Fallback message template:

```text
I still cannot read your selected calendar provider connection. We can continue planning using your preferences only, but busy times may be missing. Would you like to retry this provider, switch provider, or continue without calendar sync?
```

### Topic B: Scenario 1 Approval Gate

Topic name:

- `Scenario 1 Approval Gate`

Trigger condition:

- Agent has proposed a concrete set of study blocks

Flow:

1. Ask for explicit plan approval.
2. If approved:
   - call `saveStudyPlan` with `status = "approved"`
   - ask separate consent for calendar event creation
3. If not approved:
   - ask what to adjust
   - revise block proposal
   - loop back to approval
4. On calendar consent `yes`:
   - call `createCalendarStudyEvents` with `provider`
5. On calendar consent `no`:
   - confirm plan was saved only

Approval prompt template:

```text
Do you approve this plan as your final weekly study schedule? If yes, I will save it first, then I can add it to your selected calendar provider.
```

## 6. Tool Call Order for Scenario 1

Expected sequence for happy path:

1. `upsertStudentProfile`
2. `ingestAcademicText`
3. `extractAcademicItems`
4. `confirmAcademicItems` (only if uncertainty exists)
5. `getPlanningContext`
6. `syncCalendarBusyBlocks` (after OAuth done, with `provider`)
7. `getPlanningContext` (refresh with busy blocks)
8. `saveStudyPlan` (`status = "approved"`)
9. `createCalendarStudyEvents` (only with explicit yes, with `provider`)

## 7. Conversation Starters for Demo

Add starter prompts:

1. `Help me plan my week`
2. `I have deadlines next week, can you organize my study blocks?`
3. `I pasted my syllabus, what should I focus on first?`

## 8. Acceptance Test Checklist

Use this in Copilot Studio test chat.

1. Happy path
- Student asks weekly planning help.
- Student pastes deadlines and timezone.
- Agent runs extraction and asks clarification for ambiguous date/time.
- Agent detects missing calendar, runs OAuth handoff, resumes.
- Agent proposes blocks, gets approval, saves plan, then creates calendar events.

2. OAuth interruption path
- Student does not complete OAuth initially.
- Agent retries link and offers fallback planning without busy blocks.
- If student chooses fallback, plan is still proposed and saved.

3. Safety checks
- Agent does not invent due dates.
- Agent does not call calendar creation before approved plan save.
- Agent uses tool-grounded context before proposing final blocks.

4. Output checks
- Success response confirms saved plan id or count.
- Calendar creation response confirms created event count or links.

## 9. Quick Notes for Your Environment

- Keep `x-copilot-api-key` configured in the connector.
- Confirm deployed API base URL in OAuth link is correct.
- Ensure session identity mapping for `copilot_user_id` is stable before live demo.
