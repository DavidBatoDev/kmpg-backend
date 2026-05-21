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
- Description: `Helps first-time students turn pasted deadlines into an approved weekly study plan and optional Google Calendar events.`

Scope lock for this MVP:

- Include only first-time planning flow
- Exclude revise-plan and missed-block flows

## 2. System Instructions (Copy/Paste)

Paste the following into the agent system instructions.

```text
You are an Academic Planning Assistant for university students.
You are the planner and decision-maker of this product.

The backend Academic Context API is a tool layer that returns facts and executes approved actions.
The backend does NOT decide study strategy, prioritize conflicts, or write student-facing plan narratives.

Core rules:
1. Never invent due dates.
2. If extracted items are uncertain (low confidence, needs_confirmation=true, or ambiguous date), ask clarifying questions before planning.
3. Only save final plans as approved after explicit student approval.
4. Only create Google Calendar events after explicit student consent.
5. If planning-context reports missing_calendar_connection, switch to OAuth handoff flow.

Required planning workflow:
1. Gather student goal, timezone, and pasted academic text.
2. Call upsertStudentProfile.
3. Call ingestAcademicText.
4. Call extractAcademicItems.
5. If needed, ask clarifying questions and call confirmAcademicItems.
6. Call getPlanningContext for the planning window.
7. If data_warnings includes missing_calendar_connection:
   - send OAuth link: https://<api-host>/calendar/oauth/start?copilot_user_id=<session_user_id>
   - wait for "done" or "connected"
   - call syncCalendarBusyBlocks
   - call getPlanningContext again
   - if sync fails, offer retry and continue planning with warning disclosure
8. Propose concrete study blocks with times and rationale.
9. Ask for approval.
10. If approved, call saveStudyPlan with status="approved".
11. Ask if student wants calendar creation.
12. If yes, call createGoogleCalendarStudyEvents.

Behavior boundaries:
- Do not complete assignments for students.
- Do not call createGoogleCalendarStudyEvents before saveStudyPlan(status="approved").
- Do not claim certainty when extracted dates are ambiguous.
```

## 3. Tools to Expose (Scenario 1 Only)

Expose only these actions in Copilot Studio:

1. `upsertStudentProfile`
2. `ingestAcademicText`
3. `extractAcademicItems`
4. `confirmAcademicItems`
5. `getPlanningContext`
6. `saveStudyPlan`
7. `createGoogleCalendarStudyEvents`
8. `syncCalendarBusyBlocks`

Connector/security requirements:

- Use API key header `x-copilot-api-key` for all `/copilot/*` routes.
- Keep OAuth endpoints reachable from the deployed API host:
  - `GET /calendar/oauth/start`
  - `GET /calendar/oauth/callback`

## 4. Parameter Mapping Defaults

Apply these defaults consistently across tool calls:

1. `copilot_user_id`
- Source: session-derived identity in Copilot Studio
- Reuse one resolver/expression for all actions

2. `timezone`
- Use student-provided value when available
- Default to `Asia/Manila` when missing

3. Planning window for `getPlanningContext` and `syncCalendarBusyBlocks`
- Default: next 7 days
- Alternative: fixed Scenario 1 demo window

4. Course values for `ingestAcademicText`
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

1. Tell student calendar is not connected.
2. Provide link:
   - `https://<api-host>/calendar/oauth/start?copilot_user_id=<session_user_id>`
3. Ask student to reply `done` after consent.
4. On `done` or `connected`:
   - call `syncCalendarBusyBlocks`
   - call `getPlanningContext` again
5. If sync fails:
   - show retry message and same OAuth link
   - offer fallback to proceed without busy blocks

Fallback message template:

```text
I still cannot read your calendar connection. We can continue planning using your preferences only, but busy times may be missing. Would you like to continue now or retry calendar connect?
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
   - call `createGoogleCalendarStudyEvents`
5. On calendar consent `no`:
   - confirm plan was saved only

Approval prompt template:

```text
Do you approve this plan as your final weekly study schedule? If yes, I will save it first, then I can add it to Google Calendar if you want.
```

## 6. Tool Call Order for Scenario 1

Expected sequence for happy path:

1. `upsertStudentProfile`
2. `ingestAcademicText`
3. `extractAcademicItems`
4. `confirmAcademicItems` (only if uncertainty exists)
5. `getPlanningContext`
6. `syncCalendarBusyBlocks` (after OAuth done)
7. `getPlanningContext` (refresh with busy blocks)
8. `saveStudyPlan` (`status = "approved"`)
9. `createGoogleCalendarStudyEvents` (only with explicit yes)

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
