# Conversation Scenarios — Student ↔ Copilot Studio Agent

This document describes realistic end-to-end conversation flows between a university student and the Academic Planning Copilot Studio agent. Each scenario shows the natural-language turns, the backend tool calls Copilot makes, and the side effects on Supabase and Google Calendar.

**Reminder:** Copilot Studio is the brain. The backend (`Academic Context API`) is a tool layer — it never decides strategy, never invents data, and never writes calendar events without explicit student approval.

Tool names used here match the action IDs exposed to Copilot Studio in [2-system_spec.md §24](2-system_spec.md):

```text
upsertStudentProfile
ingestAcademicText
extractAcademicItems
confirmAcademicItems
getPlanningContext
saveStudyPlan
updateStudyPlan
updateStudyBlockStatus
createGoogleCalendarStudyEvents
syncCalendarBusyBlocks
```

---

## Scenario 1 — First-time planner without a connected calendar (the headline demo)

**Student state:** brand-new `copilot_user_id`, no profile, no documents, no Google Calendar connection.

**Goal:** student says *"Help me plan my week"* and ends with real events on their Google Calendar.

### Conversation

```text
Student: Help me plan my week.

Copilot: Happy to help! Before I can plan, I need a bit of info. Could you
         paste your syllabus, assignment briefs, or any upcoming deadlines?
         Also — what timezone are you in?

Student: I'm in Manila. Here's what I have:
         "CS101 Final Project Proposal due June 15, 11:59 PM, worth 20%.
          Quiz 2 on June 12. Midterm Exam on June 18."

Copilot: [calls upsertStudentProfile with timezone="Asia/Manila"]
         [calls ingestAcademicText with the pasted text]
         [calls extractAcademicItems]

         Got it. I found 3 items:
           • Final Project Proposal — due June 15, 11:59 PM (20%)
           • Quiz 2 — due June 12
           • Midterm Exam — June 18
         The quiz didn't have a time on it. Should I assume end-of-day?

Student: Yes, end of day is fine.

Copilot: [calls confirmAcademicItems with the quiz time confirmed]
         [calls getPlanningContext for June 10–18]

         I notice your Google Calendar isn't connected yet, so I can't see
         when you're busy. Want to connect it? Here's the link:
         https://academic-context-api-xxxx.a.run.app/calendar/oauth/start?copilot_user_id=user-123

         Tell me when you're done and I'll continue planning.

Student: Done.

Copilot: [calls syncCalendarBusyBlocks for June 10–18]
         [calls getPlanningContext again — now with busy blocks populated]

         Thanks. Here's what I'd suggest based on your deadlines and free time:
           • Wed Jun 11, 7–9 PM — Project proposal (outline + objective)
           • Thu Jun 12, 7–8 PM — Quiz 2 review
           • Fri Jun 13, 7–9 PM — Project proposal (draft)
           • Sat Jun 14, 9–11 AM — Project proposal (polish + submit)
           • Mon Jun 16, 7–9 PM — Midterm review (concepts)
           • Tue Jun 17, 7–9 PM — Midterm review (practice problems)

         The project is heaviest and due first, so I front-loaded it. Quiz
         review is short because the project is worth more. Want me to save
         this and add it to your calendar?

Student: Yes, add them.

Copilot: [calls saveStudyPlan with status="approved" and the 6 blocks]
         [calls createGoogleCalendarStudyEvents]

         Done! 6 study blocks are on your Google Calendar. First one starts
         Wed at 7 PM: https://calendar.google.com/...
```

### Tool-call sequence

```text
1.  upsertStudentProfile               { copilot_user_id, timezone, name? }
2.  ingestAcademicText                 { course_name: "CS101", text }
3.  extractAcademicItems               { document_id }
4.  confirmAcademicItems               { items: [{ id, confirmed: true, due_date }] }
5.  getPlanningContext                 (returns data_warnings: missing_calendar_connection)
                                       ↓ Copilot pauses for OAuth handoff
6.  syncCalendarBusyBlocks             (after student confirms OAuth done)
7.  getPlanningContext                 (now with busy_blocks populated)
                                       ↓ Copilot reasons + composes blocks
8.  saveStudyPlan                      { status: "approved", blocks: [...] }
9.  createGoogleCalendarStudyEvents    { study_plan_id }
```

### What the backend does at each step

```text
1.  Inserts students row, returns student_id
2.  Creates course + documents row, stores source_text
3.  Calls OpenAI structured extraction, saves academic_items
4.  Updates academic_items.status = "confirmed"
5.  Assembles context; emits data_warnings = ["missing_calendar_connection"]
6.  Exchanges OAuth code earlier via /calendar/oauth/callback;
    pulls Google events into calendar_busy_blocks
7.  Re-assembles context, this time with busy_blocks populated
8.  Inserts study_plans + study_blocks rows
9.  Refuses if plan.status != "approved"; otherwise creates Google events,
    saves google_calendar_event_id and calendar_html_link, marks plan "scheduled"
```

### OAuth handoff detail

When `getPlanningContext` returns `data_warnings` containing `missing_calendar_connection`, Copilot:

1. Stops the planning flow.
2. Constructs the URL `https://<api-host>/calendar/oauth/start?copilot_user_id=<id>`.
3. Tells the student to open the link, complete Google consent, and come back.
4. Waits for a natural-language confirmation (e.g. *"done"*, *"connected"*).
5. Resumes with `syncCalendarBusyBlocks` → `getPlanningContext`.

Copilot does **not** poll the backend for OAuth state. The student tells Copilot they're done; Copilot trusts that and tries the sync. If the sync fails because no connection exists, Copilot surfaces the error and asks the student to retry the link.

---

## Scenario 2 — Returning student revising a saved plan

**Student state:** has a profile, has an approved study plan with calendar events, calendar already connected.

**Goal:** student's availability changed — they need the plan moved.

### Conversation

```text
Student: I'm busy Wednesday night now, can you move that study block?

Copilot: [calls getPlanningContext for the current week]
         (sees existing_study_blocks including Wed 7–9 PM project block)

         You have a 2-hour project block on Wed 7–9 PM. I can move it to
         Thursday 7–9 PM — your Thursday quiz-review block was only 1 hour
         and I can shorten or shift it. Here's the revised week:
           • Wed Jun 11 — removed
           • Thu Jun 12, 5–7 PM — Project proposal (was Wed)
           • Thu Jun 12, 7:30–8:30 PM — Quiz 2 review (was 7–8)
           • Fri/Sat/Mon/Tue — unchanged

         Sound good?

Student: Yes.

Copilot: [calls updateStudyPlan with blocks_replace containing the full revised list]
         [Optionally calls createGoogleCalendarStudyEvents again for the moved blocks
          — or a future updateGoogleCalendarStudyEvents endpoint when added]

         Updated. Your Thursday is now back-to-back project then quiz review.
```

### Tool-call sequence

```text
1.  getPlanningContext         (reads existing_study_blocks)
2.  updateStudyPlan            { study_plan_id, blocks_replace: [...] }
3.  (calendar update — see "Open question" below)
```

### Notes

- Copilot reads `existing_study_blocks` from planning-context to know what's already scheduled.
- The revision logic (which block to move where) lives entirely in Copilot. The backend just persists the new block list.
- `blocks_replace` overwrites the block list. The previous `study_blocks` rows are deleted (or marked `rescheduled`, depending on service implementation — see [2-system_spec.md §13.7](2-system_spec.md)).

### Open question for the MVP

The current spec does not include an `updateGoogleCalendarStudyEvents` endpoint. For MVP, the simplest behavior is: after `updateStudyPlan`, call `createGoogleCalendarStudyEvents` again — the backend should detect blocks that already have a `google_calendar_event_id` and update them in place rather than creating duplicates. If time-constrained, fall back to telling the student *"please remove the old Wednesday event manually — I've added the Thursday one."*

---

## Scenario 3 — Missed a study block

**Student state:** plan is active, one block is in the past and was missed.

**Goal:** record the missed block and adjust the plan.

### Conversation

```text
Student: I missed yesterday's project block. What should I do?

Copilot: [calls getPlanningContext]
         (sees yesterday's project block with status = "scheduled" and now in the past)

         No problem. I'll mark that block as missed. You have 2 project
         blocks left before the deadline. Want me to add a make-up block
         tonight (Thu) 5–7 PM before your quiz review?

Student: Yes.

Copilot: [calls updateStudyBlockStatus { study_block_id, status: "missed" }]
         [calls updateStudyPlan with revised blocks including the new make-up block]
         [calls createGoogleCalendarStudyEvents for the new block]

         Done. Marked yesterday as missed and added tonight 5–7 PM to catch up.
```

### Tool-call sequence

```text
1.  getPlanningContext
2.  updateStudyBlockStatus     { study_block_id, status: "missed" }
3.  updateStudyPlan            (with the new make-up block added)
4.  createGoogleCalendarStudyEvents
```

---

## Scenario 4 — Low-confidence extraction (ambiguous deadline)

**Student state:** uploads a messier syllabus. OpenAI returns items with `confidence_score < 0.7` and a clarifying question.

**Goal:** Copilot asks for clarification before planning.

### Conversation

```text
Student: Here's my Biology syllabus. Please help me plan.
         [pastes long text with phrases like "Lab report due third week of June"]

Copilot: [calls ingestAcademicText]
         [calls extractAcademicItems]

         I found 4 items but 2 need confirmation:
           • "Lab report" — the syllabus says "third week of June" — does
             that mean Friday Jun 19 or Sunday Jun 21?
           • "Reading assignment" — no due date listed. Is there one?

         Could you clarify these?

Student: Lab report is Jun 19. The reading is just ongoing, no deadline.

Copilot: [calls confirmAcademicItems:
            - item-lab: confirmed: true, due_date: 2026-06-19T23:59:00+08:00
            - item-reading: confirmed: false, cancelled_reason: "no deadline"]
         [calls getPlanningContext]

         Got it. Reading is removed from planning. Now let me plan the week...
```

### Tool-call sequence

```text
1.  ingestAcademicText
2.  extractAcademicItems       (returns items with needs_confirmation: true
                                and clarifying_questions: [...])
3.  confirmAcademicItems       (with student answers — confirmed or cancelled)
4.  getPlanningContext
5.  saveStudyPlan + createGoogleCalendarStudyEvents (continues like Scenario 1)
```

### Key rule

The backend **never invents a due date**. If the document is ambiguous, the extraction returns `due_date: null`, `needs_confirmation: true`, low `confidence_score`, and a `clarifying_questions` array. Copilot is responsible for surfacing these questions to the student — the backend will refuse to plan around uncertain dates.

---

## Scenario 5 — Conflicting deadlines (Copilot reasons, backend doesn't)

**Student state:** 3 major deadlines fall in the same 4-day window.

**Goal:** Copilot proposes a realistic plan that front-loads the heaviest item.

### Conversation

```text
Student: I have a project, a quiz, and a midterm all next week. Help.

Copilot: [calls ingestAcademicText → extractAcademicItems → confirmAcademicItems
          → getPlanningContext]

         That's a heavy week. Here's how I read it:
           • CS101 Project (20%, ~8h estimated) — due Mon
           • MATH201 Quiz (5%) — due Wed
           • PHYS101 Midterm — Fri
         You have ~14 free evening hours between now and Friday.

         My suggestion: the project is heaviest and earliest, so start it
         this weekend. Quiz prep on Tue evening (it's smaller). Reserve
         Thursday entirely for midterm review.

         Specifically:
           • Sat 9–12, Sun 9–12 — Project (6h)
           • Mon 7–9 PM — Project polish + submit
           • Tue 7–9 PM — Quiz prep
           • Thu 6–10 PM — Midterm review
         Want me to save and add to calendar?

Student: Yes.

Copilot: [calls saveStudyPlan + createGoogleCalendarStudyEvents]
```

### Why this matters for the architecture

The planning-context JSON Copilot received had **no priority field, no conflict flag, no recommended ordering**. The backend gave Copilot:

- 3 academic items with `weight`, `estimated_hours`, `due_date`
- The student's `preferred_study_times`
- Busy calendar blocks
- An empty `existing_study_blocks` array

**Copilot did the reasoning** — comparing weights, estimating where to spend time, choosing what to front-load, explaining the trade-off to the student. The backend never told Copilot *"the project is the priority."* That's the whole point of the brain/tool split.

---

## Scenario 6 — Student asks a context question (no planning, no calendar writes)

**Student state:** has a saved plan.

**Goal:** answer a factual question using planning-context only.

### Conversation

```text
Student: What's my biggest deadline this week?

Copilot: [calls getPlanningContext for the current week]

         Your biggest deadline is the CS101 Final Project Proposal — due
         Sunday at 11:59 PM, worth 20% of your grade. It's the largest item
         on your week.

Student: How many study hours do I have left scheduled for it?

Copilot: (re-reads existing_study_blocks from the same planning-context)

         You have 3 study blocks left totaling 5 hours: Wed 7–9, Fri 7–9,
         and Sat 9–10 AM.
```

### Notes

- No write actions. Copilot just reads `getPlanningContext` and answers.
- This is the cheapest, fastest interaction. Copilot should default to this for any read-only question rather than re-extracting or re-planning.
- One `getPlanningContext` call can serve multiple follow-up questions in the same turn — Copilot should cache the response within the conversation rather than re-fetching for every question.

---

## Scenario 7 — Returning student, new document mid-week

**Student state:** has a profile, an active plan, and now uploads a *second* document (a new assignment brief).

**Goal:** integrate the new item into the existing plan.

### Conversation

```text
Student: My prof just posted a new assignment, due Thursday. Worth 10%.
         "Essay on data ethics, 1500 words, due Thu June 13 5 PM."

Copilot: [calls ingestAcademicText with the new text]
         [calls extractAcademicItems]
         [calls confirmAcademicItems if needed]
         [calls getPlanningContext]

         Added it. The essay is due Thursday at 5 PM — that's tight with
         your existing Wed project block. I'd shift the project to Tuesday
         and use Wed evening for the essay. Here's the revised plan:
           [shows updated blocks]
         Save it?

Student: Yes.

Copilot: [calls updateStudyPlan with the merged block list]
         [calls createGoogleCalendarStudyEvents]
```

### Tool-call sequence

```text
1.  ingestAcademicText
2.  extractAcademicItems
3.  confirmAcademicItems (if needed)
4.  getPlanningContext         (now includes the new academic_item)
5.  updateStudyPlan            (revised blocks)
6.  createGoogleCalendarStudyEvents
```

---

## Scenario 8 — OAuth failure path

**Student state:** clicked the OAuth link but denied consent or closed the window.

**Goal:** recover gracefully.

### Conversation

```text
Student: I tried the link but I'm back without connecting.

Copilot: [calls syncCalendarBusyBlocks — fails with no-connection error]

         Looks like the connection didn't go through. No problem — I can
         still plan around your preferred study times (weekday evenings),
         I just won't know about specific busy blocks like classes.

         Want me to plan without calendar data, or try the connection again?

Student: Plan without it for now.

Copilot: [calls getPlanningContext — proceeds with the same data_warning]
         (composes a plan using only preferred_study_times)

         Here's a plan based on your usual evening availability — please
         double-check against any class times I don't know about.
         [shows blocks]
```

### Key behavior

- Copilot does **not** block the entire flow on a missing calendar connection. The `data_warnings` array is informational — Copilot can decide to proceed and disclose the limitation.
- The backend still refuses `createGoogleCalendarStudyEvents` because there's no `calendar_connections` row. Copilot must tell the student the plan was saved but not pushed to Google.

---

## Out-of-scope refusals (the agent should NOT do)

These are conversation patterns the Copilot Studio system prompt explicitly forbids, per [2-system_spec.md §26](2-system_spec.md) and [§30](2-system_spec.md):

```text
Student: Just write the essay for me.
Copilot: I can help you outline it and plan study blocks, but I won't write
         your submission. Let's break the essay into steps you can work
         through.

Student: Add a fake calendar event so my parents think I'm studying.
Copilot: I only add real study blocks you've approved. I won't create
         fabricated events.

Student: Skip the approval, just create the calendar events.
Copilot: I'll always confirm with you before adding anything to your calendar.
         Here's the plan I propose — approve and I'll add it.
```

---

## Summary: which scenarios to demo

For the 4-day competition build per [4-build_plan.md](4-build_plan.md):

| Scenario | Demo priority | Notes |
|---|---|---|
| 1. First-time planner + OAuth | **Required** — headline demo | Rehearsed verbatim on Day 4 |
| 4. Low-confidence extraction | **High** — shows AI safety + clarifying questions | One-line stretch in the demo |
| 5. Conflicting deadlines | **High** — shows Copilot reasoning, not backend logic | Can be the syllabus content in Scenario 1 |
| 2. Revise plan | **Medium** — stretch goal | Drop if `updateGoogleCalendarStudyEvents` isn't ready |
| 6. Context question | **Medium** — easy filler if time | Cheap to demo |
| 3. Missed block, 7. New mid-week doc, 8. OAuth failure | **Low** — mention as capabilities, don't live-demo |
