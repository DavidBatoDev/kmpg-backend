# 0-reminders_notes.md

## Work IQ Outlook Calendar Capability Notes (FastAPI Proxy Plan)

This note captures Microsoft Outlook calendar operation patterns from Work IQ MCP and adapts them for our project.

Important context:

- Work IQ MCP is currently not available in our account.
- We will execute equivalent behavior through our own FastAPI backend.
- Copilot remains the planner/brain. Backend executes approved calendar actions.

---

## Source Context

- Work IQ MCP (preview): Microsoft Outlook calendar operations
- Reference link: `https://aka.ms/AboutWorkIQ`
- Copilot Studio REST API tool compatibility reference:
  - `https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-rest-api`

Read this and keep our API/tool definitions compatible with Copilot Studio expectations:

1. OpenAPI quality and format
- Prefer an OpenAPI v2-compatible definition for tool import reliability.
- Keep operation descriptions and parameter descriptions explicit, since Copilot orchestration uses them for tool selection.

2. Authentication shape
- Keep authentication clearly defined per tool/connector setup (API key or OAuth 2.0).
- Ensure required auth fields and scopes are documented for each provider mode.

3. Tool curation
- Expose only the actions Copilot should invoke for the current scenario.
- Use clear, provider-neutral action naming where possible.

4. Publishing workflow reminder
- Import spec -> configure auth -> select actions -> review parameter descriptions -> publish -> create/select connection.

---

## Capability Catalog to Replicate in FastAPI

### Event Retrieval

1. `ListEvents`
- Retrieve events with filters (start/end, title, attendees).
- For recurring meetings, returns master event only.

2. `ListCalendarView`
- Retrieve events in a range with recurring instances expanded.
- Use for selecting exact occurrences of recurring meetings.

### Event Management

3. `CreateEvent`
- Create event with attendees, recurrence, and all-day support.
- Default duration 30 minutes when time window not specified.
- Teams/online meeting link should be enabled where supported.

4. `UpdateEvent`
- Update event details (title, time, attendees, body, etc.).
- Must preserve online meeting metadata when editing meeting body:
  - Join URL
  - Meeting ID
  - Dial-in details

5. `DeleteEventById`
- Delete by event id.
- Follow provider behavior for notifications (current Work IQ note says no notifications).

### Meeting Coordination

6. `FindMeetingTimes`
- Return suggested meeting slots across participants.

### Invitation Actions

7. `AcceptEvent`
8. `TentativelyAcceptEvent`
9. `DeclineEvent`
- Optional comment should be supported.

### Forwarding

10. `ForwardEvent`
- Forward invite to additional participants.

### User and Directory Context

11. `GetUserDateAndTimeZoneSettings`
- Fetch timezone, date/time format, working hours, language.

12. `GetRooms`
- Return available rooms with names and email addresses.

### Meeting Intelligence

13. `GetOnlineMeetingTranscripts`
- Retrieve transcript (VTT) from meeting/join URL.
- If multiple transcripts exist, return all candidates.

14. `GetOnlineMeetingAiInsights`
- Primary meeting recap tool:
  - `meetingNotes`
  - `actionItems`
  - `viewpoint.mentionEvents`

Fallback rule:
- If AI insights are unavailable, use transcript retrieval and produce summary from transcript.

---

## Tool-Selection Rules for Copilot

1. Use `ListCalendarView` for:
- General search in a time window
- Recurring instance-level actions
- Safe pre-check before update/delete

2. Use `ListEvents` for:
- Master event retrieval
- Structured metadata filtering where expanded instances are not required

3. Use `GetOnlineMeetingAiInsights` for:
- Summary/recap/action-items/decisions/mentions requests

4. Always preserve online meeting metadata in `UpdateEvent` body writes.

5. Never stop on AI insight failure:
- Fallback to transcript
- Continue with best-effort summary

---

## Mapping into Our FastAPI Architecture

Since MCP is unavailable, implement these as backend provider operations behind our calendar service.

Recommended approach:

1. Keep shared calendar endpoints in Copilot contract:
- `POST /copilot/calendar/sync-busy`
- `POST /copilot/calendar/create-events`

2. Add provider-specific operation routes behind internal or extended API surface (Outlook mode), for example:
- `/copilot/calendar/events/list`
- `/copilot/calendar/events/calendar-view`
- `/copilot/calendar/events/create`
- `/copilot/calendar/events/update`
- `/copilot/calendar/events/delete`
- `/copilot/calendar/meetings/find-times`
- `/copilot/calendar/invitations/accept`
- `/copilot/calendar/invitations/tentative`
- `/copilot/calendar/invitations/decline`
- `/copilot/calendar/events/forward`
- `/copilot/calendar/settings/user-timezone`
- `/copilot/calendar/rooms/list`
- `/copilot/calendar/meetings/transcripts`
- `/copilot/calendar/meetings/insights`

3. Require `provider` in requests:
- `provider = "outlook"` for these operations
- Keep dual-provider contract compatible with `google`

4. Preserve core policy:
- Calendar writes only after plan approval
- Student scoping via `copilot_user_id -> student_id`
- No direct strategy generation in backend

---

## Data and Security Notes

1. Tokens:
- Store encrypted provider tokens only.
- Never log raw tokens, secrets, or auth headers.

2. Event IDs:
- Keep provider event id in persistent block linkage.
- Current legacy field naming (`google_calendar_event_id`) may need neutral migration (`calendar_event_id`).

3. Auditing:
- Log action name, status, duration, sanitized payload.

---

## MVP Priority Suggestion (Outlook Path)

1. Retrieval + availability first:
- `ListCalendarView`
- `FindMeetingTimes`
- `GetUserDateAndTimeZoneSettings`

2. Core writes:
- `CreateEvent`
- `UpdateEvent`
- `DeleteEventById`

3. Invite actions:
- `AcceptEvent`, `TentativelyAcceptEvent`, `DeclineEvent`, `ForwardEvent`

4. Intelligence:
- `GetOnlineMeetingAiInsights`
- Fallback `GetOnlineMeetingTranscripts`

---

## Operational Reminder

Copilot must ask the user which provider to use (Google vs Outlook) before connect/sync/create/update/delete actions when provider is not already known in conversation context.
