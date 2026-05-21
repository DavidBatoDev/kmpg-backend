# Project Overview: Academic Planning AI Agent

We are building an **AI-powered academic planning assistant** for university students using **Microsoft Copilot Studio as the main agent and the brain of the system**. The goal is to help students turn scattered academic information — syllabi, assignment briefs, exam dates, course requirements, personal goals, and calendar availability — into a clear, adaptive study strategy.

Instead of acting like a simple chatbot or reminder tool, this agent will actively help students understand what they need to do, when they need to do it, and how to realistically manage their workload. The student can ask natural language requests such as *"Help me plan my week,"* *"What should I study today?"* or *"I have three deadlines next week, can you help me organize them?"* The Copilot Studio agent then calls a backend **Academic Context API** to fetch accurate, structured information and uses that information to propose, revise, and explain a study plan.

The product is built with **Microsoft Copilot Studio as the agent and decision-maker**, **Python/FastAPI as the Academic Context API deployed on Google Cloud Run**, **Supabase Postgres with pgvector for structured and semantic academic data**, **Supabase Storage for uploaded files**, **OpenAI as a backend extraction/embedding utility (not a planner)**, and **Calendar provider integration (Google Calendar or Outlook Calendar)** for scheduling approved study blocks.

---

# The Challenge

University students often struggle to manage academic requirements because their responsibilities are spread across multiple documents, platforms, calendars, and personal notes. A student may have one syllabus in PDF form, an assignment brief in another document, exam reminders in an LMS, class schedules in a calendar, and personal study goals only in their head.

The problem is not just that students forget deadlines. The bigger issue is that students often do not realize early enough when multiple deadlines, exams, projects, and personal commitments are colliding. By the time they notice the conflict, there may no longer be enough time to prepare properly. This leads to rushed submissions, poor prioritization, stress, missed work, and reduced academic performance.

Most existing tools only help students **record tasks** or **set reminders**. They do not deeply understand the relationship between deadlines, workload, available study time, course difficulty, and student goals. A to-do list can tell a student that an essay is due next Friday, but it does not automatically know that the same student also has an exam, a group project, and limited availability that week.

Our challenge is to build an AI agent that goes beyond reminders and becomes a proactive academic planning assistant.

---

# What We Are Trying to Build

We are building an **autonomous academic assistant** that transforms static academic requirements into an active, adaptive study plan.

The Copilot Studio agent collects or receives academic inputs, asks the backend to extract key requirements into structured academic items, requests planning context from the backend, then reasons about deadlines, workload, and availability to recommend realistic study blocks. When the student's availability changes, Copilot revises the plan and asks the backend to update the saved schedule.

For example, a student could upload a syllabus and say:

> "Help me plan my week."

Copilot asks the backend to extract academic items, fetches planning context (deadlines + busy calendar blocks + preferences), and then composes the plan itself. It explains its reasoning, asks for the student's approval, and only then asks the backend to create calendar provider events.

This means the agent is not just responding to questions. Copilot is actively orchestrating the student's academic workflow, while the backend serves accurate facts and executes approved actions.

---

# Core Product Concept

The product acts as a **study planning agent**, not an assignment-writing agent.

Its purpose is to help students:

* Understand upcoming academic requirements
* Break large academic tasks into manageable study blocks
* Detect deadline conflicts before they become urgent
* Plan around real calendar availability
* Adjust their schedule when something changes
* Stay accountable without being replaced by the system

The agent supports the student's decision-making, but the student remains responsible for attending classes, completing work, submitting assignments, and meeting deadlines.

This distinction is important. We are not building a tool that completes schoolwork for students. We are building a tool that helps students manage time, workload, and priorities more intelligently.

---

# User Roles

The primary users are **students**.

Students will provide the academic inputs, connect their calendar, review suggested plans, approve schedule changes, and make final decisions about their study strategy. They can use the agent to ask for help in natural language, upload documents, clarify deadlines, revise schedules, and check what they should focus on next.

The system supports students, but it does not replace them. Copilot provides structure, recommendations, reminders, and reasoning, but the responsibility for academic action remains with the student.

---

# Proposed Solution

The proposed solution is an AI agent inside **Microsoft Copilot Studio** connected to a custom **Academic Context API**.

**Copilot Studio is the brain.** It manages the conversation, interprets student requests, calls backend tools, decides what study plan to propose, writes the plan narrative, explains priorities, and revises plans conversationally.

**The FastAPI backend is the data and tool layer.** It stores student data, processes academic documents, extracts deadlines, returns planning context, saves Copilot-created study plans, and executes approved calendar provider actions. The backend does *not* propose study strategy, revise plans on its own, or generate motivational guidance.

Supabase stores the student profile, courses, uploaded documents, extracted academic items, saved study plans, study blocks, and calendar event references. Supabase Storage handles uploaded files. pgvector enables semantic search over academic documents.

**OpenAI is used in the backend only as an extraction and embedding utility** — pulling structured facts out of messy syllabus text, generating embeddings for semantic search, and summarizing source document sections so Copilot has clean context to reason over. OpenAI in the backend never decides the study plan or advises the student.

Calendar provider support is integrated immediately so that approved study plans can become real calendar events.

---

# Architecture at a Glance

```text
Microsoft Copilot Studio
= Brain, planner, advisor, conversation, decision-making

FastAPI Academic Context API
= Data service, storage, retrieval, document processing, calendar execution

Supabase Postgres + Storage
= Source of truth

OpenAI in backend
= Extraction/embedding utility (not a planner)

Google Calendar or Outlook Calendar
= External action system
```

The backend should **not** say:

> "Here is the recommended study plan..."

Instead, the backend returns structured context such as:

```json
{
  "student_profile": {},
  "courses": [],
  "upcoming_academic_items": [],
  "busy_calendar_blocks": [],
  "study_preferences": [],
  "previous_study_blocks": [],
  "document_context": [],
  "data_warnings": []
}
```

Then Copilot Studio uses that information to say:

> "Based on your deadlines and free time, I suggest working on the project first, then reserving Thursday for quiz review."

---

# High-Level System Flow

1. The student asks the Copilot Studio agent for help, e.g. *"Help me plan my week."*
2. Copilot checks whether the system already has the student's courses, deadlines, availability, and academic documents. If something is missing, Copilot asks the student to upload a syllabus, paste deadlines, or connect a calendar provider (Google Calendar or Outlook Calendar).
3. Once academic input is available, the backend processes the document, extracts factual academic items via OpenAI structured outputs, and stores them in Supabase.
4. Copilot calls `GET /copilot/planning-context` to fetch the full picture: deadlines, busy calendar blocks, study preferences, prior study blocks, document context, and data warnings.
5. **Copilot reasons over that context** and proposes a study plan in natural language. It explains the priorities itself — the backend did not score them.
6. The student approves.
7. Copilot calls `POST /copilot/study-plans/save` with the blocks it composed, then `POST /copilot/calendar/create-events` to push them to the selected calendar provider.
8. If the student says *"I'm busy Wednesday"* or *"I missed yesterday's study block,"* Copilot revises the plan itself and calls `POST /copilot/study-plans/update` to persist the revision.

---

# What Makes This an AI Agent

Copilot Studio is what makes this an AI agent. It reasons across goals, tools, and changing context.

It does not only answer questions. It decides when to extract requirements, when to fetch planning context, what plan to propose, how to explain prioritization, and when to ask for approval before calendar writes. It adapts when new information appears.

Copilot has:
- A clear objective: help the student manage academic workload more effectively.
- Tools: the Academic Context API endpoints for data, extraction, persistence, and calendar execution.
- Memory/context: student profile, courses, deadlines, preferences, and past study blocks (all retrieved from the backend on demand).
- Decision-making behavior: asking clarifying questions, identifying conflicts, recommending priorities, and revising plans.

---

# MVP Scope

For the first version, we should focus on a strong vertical slice:

**Upload syllabus → Extract academic items → Copilot fetches planning context → Copilot proposes plan → Student approves → Save plan → Create calendar provider events.**

This MVP is enough to show the main value of the product. It proves that Copilot can turn academic documents into structured planning actions and create a real study schedule based on the student's workload — while the backend stays focused on clean data, extraction, persistence, and calendar execution.

The MVP should include document upload/ingest, deadline extraction, student confirmation of low-confidence items, planning context retrieval, plan save, and calendar provider event creation.

We should avoid overbuilding too early. LMS integrations, advanced analytics, multi-agent architecture, and institution-level dashboards can come later.

---

# Success Criteria

The project is successful if Copilot can help a student move from scattered academic information to a clear, calendar-ready study plan with minimal manual work — using only the structured facts the backend serves.

A successful demo should show that Copilot can request academic inputs, ask the backend to extract them, request planning context, propose a realistic plan, explain its reasoning, ask for approval, and trigger calendar provider event creation through the backend.

The strongest demo scenario:

A student uploads a syllabus, Copilot asks the backend to extract several upcoming requirements, fetches planning context, notices three major deadlines in the same week, proposes an adjusted study plan with its own reasoning, and asks the backend to add the approved schedule to the selected calendar provider.

That directly answers the challenge: students do not just need another reminder tool. They need an adaptive academic assistant that helps them plan ahead before stress and conflicts become unmanageable — and the brain doing the adapting is Copilot Studio, served by a clean, accurate Academic Context API.
