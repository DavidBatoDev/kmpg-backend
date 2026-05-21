# Supabase setup & MCP for kmpg-backend

How to apply database migrations and connect **Supabase MCP** in Cursor for this project.

---

## 1. What’s in the repo

| Path | Purpose |
|------|---------|
| `supabase/migrations/20260521120000_init_academic_context_schema.sql` | All 11 tables + storage bucket + vector search + RLS |
| `supabase/seed.sql` | Demo student `demo-user-1` |
| `supabase/config.toml` | Local Supabase CLI config (`project_id = kmpg-agent`) |

**Tables created:** `students`, `courses`, `documents`, `document_chunks`, `academic_items`, `calendar_connections`, `calendar_busy_blocks`, `study_plans`, `study_blocks`, `oauth_states`, `agent_action_logs`

---

## 2. Prerequisites

1. **Docker Desktop** — running (required for local Supabase).
2. **Supabase CLI** — install:

   ```powershell
   scoop install supabase
   # or: npm install -g supabase
   ```

   Verify: `supabase --version`

3. **Supabase account** — https://supabase.com/dashboard (for hosted project).

---

## 3. Option A — Local Supabase (fastest for dev)

From repo root:

```powershell
cd c:\Users\User\CODERIST\hackathon\kmpg-backend

# First time: starts Postgres + Studio locally
supabase start

# Apply migrations + seed
supabase db reset
```

`supabase status` prints local URLs and keys. Copy into `.env`:

```env
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_ROLE_KEY=<service_role key from supabase status>
SUPABASE_STORAGE_BUCKET=academic-documents
```

Open local Studio: http://127.0.0.1:54323

Verify tables: **Table Editor** → you should see all 11 tables + `demo-user-1` in `students`.

---

## 4. Option B — Hosted Supabase (hackathon / demo)

### 4.1 Create project

1. Dashboard → **New project** → pick region, set DB password.
2. Note **Project URL**, **service_role** key (Settings → API), and **Project ref** (Settings → General).

### 4.2 Link CLI and push migrations

```powershell
cd c:\Users\User\CODERIST\hackathon\kmpg-backend

supabase login
supabase link --project-ref YOUR_PROJECT_REF
# Enter database password when prompted

supabase db push
```

Optional seed on remote (run in SQL Editor or after linking):

```powershell
# Or paste supabase/seed.sql in Dashboard → SQL Editor → Run
```

### 4.3 `.env` for FastAPI

```env
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...   # service_role — server only, never commit
SUPABASE_STORAGE_BUCKET=academic-documents
SUPABASE_PROJECT_REF=YOUR_PROJECT_REF
```

Restart uvicorn. `GET /health` should show `"supabase_configured": true` once URL + key are set.

### 4.4 Test APIs

```powershell
$headers = @{ "x-copilot-api-key" = "YOUR_COPILOT_API_KEY"; "Content-Type" = "application/json" }

Invoke-RestMethod -Method POST -Uri "http://localhost:8000/copilot/students/upsert" -Headers $headers -Body (@{
  copilot_user_id = "demo-user-1"
  name = "Demo Student"
  timezone = "Asia/Manila"
} | ConvertTo-Json)

Invoke-RestMethod -Method POST -Uri "http://localhost:8000/copilot/documents/ingest-text" -Headers $headers -Body (@{
  copilot_user_id = "demo-user-1"
  course_name = "Introduction to Programming"
  document_name = "CS101 syllabus"
  text = "Assignment 1 due June 12. Final project due June 15 at 11:59 PM, worth 20 percent."
} | ConvertTo-Json)
```

---

## 5. Connect Supabase MCP in Cursor (recommended)

MCP lets the AI agent query your Supabase project, run SQL, and manage schema from chat.

### Option A — One-click (easiest)

1. Supabase Dashboard → your project → **Connect** / **MCP** section.  
2. Click **Add to Cursor** (installs MCP for this project).  
3. Or paste the generated config into `.cursor/mcp.json`.

**Hackathon project ref:** `yltcmogqavtwvxvxmqxq`  
**Do not use:** `ifzyntqwymmgimnxtguz` (wrong project — academic tables were removed from there).

```json
{
  "mcpServers": {
    "supabase": {
      "url": "https://mcp.supabase.com/mcp?project_ref=yltcmogqavtwvxvxmqxq"
    }
  }
}
```

After changing `mcp.json`, **disconnect and re-authenticate** Supabase MCP in Cursor so OAuth matches this project ref.

Copy from example if needed:

```powershell
copy .cursor\mcp.json.example .cursor\mcp.json
# Replace YOUR_PROJECT_REF with yltcmogqavtwvxvxmqxq (or your ref)
```

`.cursor/mcp.json` is gitignored — safe to keep your project ref there.

### Option B — Legacy npx + Personal Access Token

If the URL method fails, use a PAT from https://supabase.com/dashboard/account/tokens:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--access-token",
        "YOUR_SUPABASE_ACCESS_TOKEN",
        "--project-ref",
        "yltcmogqavtwvxvxmqxq"
      ]
    }
  }
}
```

### Enable in Cursor

1. **Cursor Settings** → **Tools & MCP**.  
2. Turn **supabase** on (green / active).  
3. First connection may open **Supabase OAuth** in the browser — sign in and approve.  
4. Restart Cursor if the server does not appear.

Cursor docs: https://docs.cursor.com/context/mcp

### Verify MCP

In Composer:

> List tables in my Supabase project.

> Apply pending migrations or confirm `students` table exists.

### Optional — Supabase Agent Skills

Gives Cursor/Composer better defaults for Supabase workflows:

```powershell
npx skills add supabase/agent-skills
```

Run once per machine (or per user). Not required for MCP to work.

### Security notes

| Do | Don’t |
|----|--------|
| Keep `.cursor/mcp.json` local (gitignored) | Commit service_role key |
| Use MCP for schema/SQL in dev | Paste service_role into MCP config |
| FastAPI uses `SUPABASE_SERVICE_ROLE_KEY` in `.env` only | Expose service_role to Copilot or frontend |

Official MCP docs: https://supabase.com/docs/guides/getting-started/mcp

---

## 6. MCP vs FastAPI `.env`

| Credential | Used by | Purpose |
|------------|---------|---------|
| **MCP URL + OAuth** | Cursor MCP (`mcp.json` url) | AI tools in IDE — no PAT needed with hosted MCP |
| **PAT** (`sbp_...`) | Legacy npx MCP only | If you use Option B above |
| **service_role** (`eyJ...`) | FastAPI `app/db/supabase.py` | Backend API at runtime |
| **anon** key | Not used in MVP | Future browser client |

**Project ref for this repo:** `yltcmogqavtwvxvxmqxq`  
**Supabase URL:** `https://yltcmogqavtwvxvxmqxq.supabase.co`  

MCP OAuth may still point at another project until you re-auth — check with `get_project_url` or list tables in chat.

MCP does not replace `SUPABASE_SERVICE_ROLE_KEY` in `.env`.

---

## 7. Common commands

```powershell
supabase start          # local stack
supabase stop
supabase status         # URLs + keys
supabase db reset       # re-apply migrations + seed (local)
supabase db push        # push migrations to linked remote
supabase migration list
supabase db pull        # pull remote schema changes
```

---

## 8. Troubleshooting

| Issue | Fix |
|-------|-----|
| `vector` extension fails | Enable **pgvector** in hosted project: Database → Extensions |
| `supabase db push` auth failed | `supabase login` again; check project ref |
| FastAPI 503 Supabase not configured | Set `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in `.env` |
| Upsert 500 / relation does not exist | Run `supabase db push` or `supabase db reset` |
| MCP not showing | Node.js installed; restart Cursor; check `npx` works |
| HNSW index warning locally | Usually fine on empty table; ignore unless insert fails |

---

## 9. Next after migrations

1. Confirm `demo-user-1` in Studio.  
2. Test `POST /copilot/students/upsert` and `ingest-text`.  
3. Implement Phase 2: `extraction_service` + `planning_context_service`.  

See [ROADMAP.md](../ROADMAP.md) Phase 1–2.
