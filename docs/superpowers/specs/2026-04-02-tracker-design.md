# Tracker — Design Spec
**Date:** 2026-04-02
**Status:** Approved

## Overview

A kanban/dashboard web app for tracking AI-assisted coding projects. Designed specifically for workflows where LLMs (Claude, Kimi, etc.) pick up feature cards, do the work, and report progress in real time. Exposes a full REST API, WebSocket feed, and MCP backend so LLMs can interact with the tracker natively.

---

## Architecture

### Docker

Single Docker container. FastAPI serves everything on one port:

| Endpoint | Purpose |
|---|---|
| `GET /` | React app (pre-built static files) |
| `/api/v1/` | REST API |
| `/ws/` | WebSocket real-time feed |
| `/mcp/` | MCP server (tools + resources, HTTP/SSE) |

SQLite database is mounted as a volume (`./data/tracker.db`) so it persists across restarts.

### Project layout

```
tracker/
├── backend/
│   ├── main.py          # FastAPI app entry point
│   ├── api/             # REST route handlers
│   ├── mcp/             # MCP tools and resources
│   ├── scanner/         # Project folder scanner
│   ├── models/          # SQLAlchemy models + SQLite
│   └── ws/              # WebSocket manager
├── frontend/
│   └── src/             # React + Vite app
├── Dockerfile
└── docker-compose.yml
```

### Project scanning

The scanner mounts the host's `/Users/donaldrich/Projects` folder into the container and detects projects that meet both criteria:
1. Contains a `.git` directory
2. Contains at least one known project file: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Dockerfile`, `docker-compose.yml`

Scanning runs:
- Automatically on container startup
- On demand via `POST /api/v1/projects/scan` (UI "Rescan" button and MCP tool)

When a previously-scanned folder disappears, the project is marked `active: false` rather than deleted, preserving card history.

---

## Data Model

### `projects`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | Slug derived from folder name (e.g. `mcp-hub`) |
| `name` | TEXT | Display name |
| `path` | TEXT | Absolute path on host |
| `stack` | JSON array | Auto-detected tags e.g. `["python","docker"]` |
| `git_branch` | TEXT | Current branch |
| `git_dirty` | BOOLEAN | Uncommitted changes present |
| `git_last_commit` | TEXT | Last commit message |
| `description` | TEXT | Pulled from README.md first paragraph if present |
| `scanned_at` | DATETIME | |
| `active` | BOOLEAN | False if folder no longer exists |

### `cards`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `project_id` | TEXT FK | → projects |
| `title` | TEXT | |
| `description` | TEXT | Markdown |
| `status` | ENUM | `todo` \| `in_progress` \| `review` \| `done` \| `blocked` |
| `priority` | ENUM | `low` \| `medium` \| `high` |
| `assigned_llm` | TEXT | `"claude"`, `"kimi"`, `"user"`, etc. |
| `tags` | JSON array | Free-form labels |
| `linked_files` | JSON array | Relative paths within the project |
| `acceptance` | TEXT | Markdown checklist of done criteria |
| `blocks` | JSON array | Card IDs this card blocks |
| `blocked_by` | JSON array | Card IDs that must complete before this one |
| `created_at` | DATETIME | |
| `started_at` | DATETIME | Set when status moves to `in_progress` |
| `completed_at` | DATETIME | Set when status moves to `done` |

### `card_events`

One table handles logs, milestones, status changes, and assignments. Differentiated by `type`.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `card_id` | TEXT FK | → cards |
| `type` | ENUM | `log` \| `milestone` \| `status_change` \| `assignment` |
| `body` | TEXT | The message or content |
| `actor` | TEXT | `"claude"`, `"kimi"`, `"user"` |
| `meta` | JSON | Type-specific data e.g. `{"from":"todo","to":"in_progress"}` |
| `created_at` | DATETIME | |

Every card_event is broadcast over the WebSocket so the UI updates in real time without polling.

### `webhooks`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `url` | TEXT | POST target |
| `events` | JSON array | e.g. `["card.status_changed","card.created"]` |
| `active` | BOOLEAN | |

---

## REST API

Base path: `/api/v1/`

### Projects
- `GET /projects` — list all (filterable by `active`)
- `GET /projects/{id}` — project detail + card summary
- `PATCH /projects/{id}` — update name or description
- `POST /projects/scan` — trigger re-scan

### Cards
- `GET /projects/{id}/cards` — list cards (filterable by `status`, `priority`, `tag`, `assigned_llm`)
- `POST /projects/{id}/cards` — create card
- `GET /cards/{id}` — full card detail
- `PATCH /cards/{id}` — update any card field
- `DELETE /cards/{id}` — delete card

### Card Events
- `GET /cards/{id}/events` — full event history (filterable by `type`)
- `POST /cards/{id}/log` — append a log line
- `POST /cards/{id}/milestone` — add a milestone

### Search & Webhooks
- `GET /search?q=` — full-text search across all cards (title, description, body)
- `GET /webhooks` — list registered webhooks
- `POST /webhooks` — register a webhook
- `DELETE /webhooks/{id}` — remove a webhook

### WebSocket
- `WS /ws/cards/{id}` — live event stream for a single card
- `WS /ws/projects/{id}` — all card_events for a project board (used by the kanban UI)

---

## MCP Server

Transport: HTTP with SSE (`/mcp/`). Compatible with Claude Code and any MCP-aware client.

### Tools

| Tool | Description |
|---|---|
| `list_projects` | All projects with stack tags and git status |
| `list_cards` | Cards for a project. Accepts `status`, `priority`, `tag` filters. |
| `get_card` | Full card detail including all events |
| `claim_card` | Assign card to an LLM and move to `in_progress` |
| `get_context_bundle` | Card + project file tree + recent git log + linked file contents — everything needed to start work in one call |
| `update_card_status` | Move card through status workflow |
| `post_log` | Append a timestamped log line |
| `post_milestone` | Add a structured progress checkpoint |
| `create_card` | Create a new card (for LLM-discovered sub-tasks) |
| `search_cards` | Full-text search across all projects |
| `trigger_scan` | Re-scan the projects folder |

### Resources

| URI | Description |
|---|---|
| `tracker://projects` | List of all projects |
| `tracker://projects/{id}` | Project detail + card summary |
| `tracker://cards/{id}` | Full card + events |
| `tracker://cards/{id}/context` | Context bundle as a browsable resource |

---

## Web UI

**Stack:** React + Vite, served as pre-built static files by FastAPI.

### Layout
- **Top nav:** App logo, global search, Webhooks settings, Rescan button
- **Project tabs:** Tab strip (or left sidebar) listing all active projects. Click to open that project's board.

### Project Board
- Header shows: project name, current git branch, dirty indicator, last commit message, view toggle (Kanban / List)
- **Kanban view (default):** Four columns — Todo, In Progress, Review, Done. Cards show title, tags, priority colour, assigned LLM, and a live indicator when an LLM is actively posting logs.
- **List view:** Same cards in a compact vertical list grouped by status.
- "Add card" button at the bottom of the Todo column.

### Card Detail
- Slide-out panel (no navigation away from the board)
- Left side: description, acceptance criteria checklist, linked files, dependencies (blocks/blocked-by)
- Right side: live log stream (WebSocket-fed, auto-scrolling), milestones list
- Status and assignee editable inline

### Real-time Updates
- The board subscribes to `WS /ws/projects/{id}` on mount
- Card status changes, new log lines, and milestones update the UI instantly without a page refresh

---

## Additional Features

### LLM Context Bundle
`get_context_bundle` MCP tool / `tracker://cards/{id}/context` resource returns:
- Card detail (title, description, acceptance criteria, linked files)
- Project file tree (up to 3 levels deep)
- Last 10 git commits
- Content of each linked file

### Tech Stack Auto-detection
Scanner reads project root for manifest files and assigns tags:

| File | Tags |
|---|---|
| `package.json` | `node` |
| `pyproject.toml` / `setup.py` | `python` |
| `Cargo.toml` | `rust` |
| `go.mod` | `go` |
| `Dockerfile` | `docker` |
| `docker-compose.yml` | `compose` |

### Git Status
Populated at scan time using `gitpython`. Refreshed on each manual scan. Shown on the board header.

### Webhooks
Fired as HTTP POST on these events: `card.created`, `card.status_changed`, `card.assigned`, `card.completed`, `project.scanned`. Payload includes the full card object.

### Full-text Search
SQLite FTS5 extension on `cards(title, description, acceptance)` and `card_events(body)`. Available in UI global search and via `search_cards` MCP tool.

### Audit Trail
Every mutation (status change, assignment, log, milestone) writes a `card_event` record. The full history is visible in the card detail panel and queryable via the API.

---

## Out of Scope

- Authentication (single-user, LAN-only app)
- Multiple users / permissions
- Drag-and-drop between kanban columns (status change via dropdown/button instead)
- Mobile-optimised layout
