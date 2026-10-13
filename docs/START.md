# 🚀 START GUIDE — Industrial Knowledge Intelligence Platform

Everything you need to start the project and use it. Follow the sections in order.

> **Project root:** `c:\Users\Nitesh\OneDrive\Desktop\ET hackathon`
> Commands below assume **PowerShell** (your default shell). Run them from the project root unless a `cd` says otherwise.

---

## 0. Prerequisites (one-time — already done on this machine)

| Tool | Check command | Notes |
|---|---|---|
| Docker Desktop | `docker --version` | Must be **running** (whale icon in tray) |
| Ollama | `ollama --version` | Must be running; provides the free cloud models |
| Python 3.10+ | `python --version` | Backend deps already installed |
| Node 18+ | `node --version` | Frontend deps already installed |

**Ollama cloud models (one-time pull — already done):**
```powershell
ollama pull gpt-oss:20b-cloud
ollama pull gpt-oss:120b-cloud
```
> These run on Ollama's servers (free). Your machine just proxies to them — no GPU needed. You must be signed in: `ollama signin` (once).

---

## 1. ▶️ EVERY-TIME STARTUP (4 steps)

Open **4 separate PowerShell windows** (or tabs). Keep windows 2–4 open while using the app.

### Step 1 — Make sure Docker Desktop + Ollama are running
- Start **Docker Desktop** (wait until it says "Engine running").
- Ollama usually auto-starts. Verify: `ollama list` (should show `gpt-oss:20b-cloud`, `gpt-oss:120b-cloud`).

### Step 2 — Start the data stores (Postgres, Neo4j, Qdrant, MinIO)
```powershell
cd "c:\Users\Nitesh\OneDrive\Desktop\ET hackathon"
docker compose up -d postgres neo4j qdrant minio
```
Wait ~20 seconds, then confirm all are healthy:
```powershell
docker compose ps
```
You want `postgres`, `neo4j`, `qdrant`, `minio` all **Up** (postgres/neo4j show **healthy**).

### Step 3 — Start the backend (FastAPI, port 8000)
```powershell
cd "c:\Users\Nitesh\OneDrive\Desktop\ET hackathon\backend"
python -m uvicorn main:app --port 8000 --reload
```
Leave this running. Confirm in a browser: <http://localhost:8000/health> → should return `{"status":"ok", ...}`.

### Step 4 — Start the frontend (Next.js, port 3000)
```powershell
cd "c:\Users\Nitesh\OneDrive\Desktop\ET hackathon\frontend"
npm run dev
```
Leave this running.

### ✅ Open the app
**<http://localhost:3000>**

---

## 2. 🧭 First-time usage flow

1. Go to **Upload** → drag in `sample_data\pump_P-101_maintenance_report.txt` and `sample_data\inspection_records.csv`. Watch the progress bars complete.
2. Go to **Dashboard** → see document/chunk/graph counts populate.
3. Go to **Copilot** → ask *"Why did pump P-101 fail and how was it fixed?"* → grounded answer with citations.
4. Go to **Knowledge Graph** → see P-101 connected to people, procedures, regulations. Click a node for details.
5. Go to **RCA** → enter `P-101` → structured root-cause report.
6. Go to **Compliance** → "Run Compliance Scan" → gap analysis (takes ~1 min, 6 model calls).
7. Go to **Lessons** → "Discover Patterns" + similar-incident search.

> ⏱️ First model call after startup can take 10–30s (cloud cold start). Compliance/Lessons run several calls, so give them a minute.

---

## 3. 🗄️ Viewing the data stores

### A) Knowledge Graph — Neo4j Browser (the visual graph)
1. Open **<http://localhost:7474>** in your browser.
2. Connect form:
   - **Connect URL:** `bolt://localhost:7687`
   - **Username:** `neo4j`
   - **Password:** `change_me_neo4j`
3. Run queries in the top bar (Cmd/Ctrl+Enter to execute):

```cypher
// See the whole graph
MATCH (n) RETURN n LIMIT 200

// Everything connected to pump P-101
MATCH (e:Equipment {tag:'P-101'})-[r]-(m) RETURN e, r, m

// Count nodes by type
MATCH (n) RETURN labels(n)[0] AS type, count(*) AS count ORDER BY count DESC

// All regulations referenced
MATCH (r:Regulation) RETURN r

// Wipe the graph (careful!) — useful before a clean demo
MATCH (n) DETACH DELETE n
```

### B) Relational DB — PostgreSQL (documents, jobs, chat, RCA reports)
Our Postgres runs on host port **55432** (not 5432 — your machine already has native PostgreSQL on 5432/5433).

**Option 1 — Quick CLI inside the container:**
```powershell
docker exec -it ikb_postgres psql -U ikb -d industrial_kb
```
Then at the `industrial_kb=#` prompt:
```sql
\dt                                  -- list tables
SELECT id, filename, doc_type, chunk_count FROM documents;
SELECT id, status, stage, progress FROM jobs ORDER BY created_at DESC LIMIT 10;
SELECT role, left(content, 60) FROM chat_history ORDER BY created_at;
SELECT asset_tag, confidence FROM rca_reports;
\q                                   -- quit
```

**Option 2 — GUI tool (DBeaver / pgAdmin / TablePlus):** create a new PostgreSQL connection with:
| Field | Value |
|---|---|
| Host | `localhost` |
| Port | **`55432`** |
| Database | `industrial_kb` |
| Username | `ikb` |
| Password | `change_me_postgres` |

### C) Vector store — Qdrant dashboard
Open **<http://localhost:6333/dashboard>** → click the `industrial_chunks` collection to browse embedded chunks and run vector searches.

### D) File storage — MinIO console
Open **<http://localhost:9001>** and log in:
- **Username:** `minioadmin`
- **Password:** `change_me_minio`

Raw uploaded files live in the `industrial-docs` bucket.

---

## 4. ⏹️ Stopping the project

- **Backend / Frontend:** press `Ctrl + C` in each of their PowerShell windows.
- **Data stores (keep data):**
  ```powershell
  cd "c:\Users\Nitesh\OneDrive\Desktop\ET hackathon"
  docker compose stop
  ```
- **Data stores (delete ALL data — fresh slate):**
  ```powershell
  docker compose down -v
  ```
  > `-v` removes the volumes (Postgres rows, Neo4j graph, Qdrant vectors, MinIO files). Use this only when you want to start completely clean.

---

## 5. 🌐 All URLs at a glance

| Service | URL | Login |
|---|---|---|
| **App (frontend)** | <http://localhost:3000> | — |
| Backend API docs | <http://localhost:8000/docs> | — |
| Backend health | <http://localhost:8000/health> | — |
| Neo4j Browser (graph) | <http://localhost:7474> | neo4j / change_me_neo4j |
| Qdrant dashboard | <http://localhost:6333/dashboard> | — |
| MinIO console (files) | <http://localhost:9001> | minioadmin / change_me_minio |
| PostgreSQL (DB tool) | localhost:**55432** | ikb / change_me_postgres |

---

## 6. 🛠️ Troubleshooting

| Symptom | Fix |
|---|---|
| Dashboard says "Backend unreachable" | Backend window not running, or not on port 8000. Restart Step 3. |
| Chat/RCA/Compliance hang or error | Ollama not running or not signed in. Run `ollama list`; if empty, `ollama signin` then re-pull the two `-cloud` models. |
| `docker compose ps` shows nothing | Docker Desktop isn't running. Start it, wait for "Engine running", retry Step 2. |
| Postgres connection fails on 5432 | Use port **55432** — 5432/5433 are your native PostgreSQL installs, not this project. |
| Port 8000 / 3000 already in use | Find & stop the process: `netstat -ano | findstr :8000` → `taskkill /PID <pid> /F`. |
| Frontend won't start | `cd frontend; npm install` then `npm run dev`. |
| Backend import errors | `cd backend; pip install -r requirements.txt`. |
| Want a clean demo | Wipe stores (`docker compose down -v`), restart, re-upload sample docs. |

---

## 7. 📦 What's where

| Path | Contents |
|---|---|
| `backend/` | FastAPI app, agents, parsers, graph, vector store |
| `frontend/` | Next.js UI |
| `sample_data/` | Demo documents to upload |
| `docker-compose.yml` | The 4 data stores (+ optional containerized backend/frontend) |
| `.env` | Secrets & config (already filled in) |
| `PLAN.md` / `PROGRESS.md` / `LOG.md` / `ARCHITECTURE.md` | Project docs |

---

> 💡 **Tip:** The data stores (Step 2) can stay running in the background across sessions. On most days you'll only need to restart the **backend** (Step 3) and **frontend** (Step 4).
