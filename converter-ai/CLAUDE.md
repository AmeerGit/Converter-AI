# converter-ai

A Vue 3 → React migration tool. The UI (`ui/`) lets a user submit a public GitHub repo URL and click Migrate; the API (`api/`) clones that repo, runs an agentic Claude loop to migrate it, and returns a downloadable, runnable Vite React project as a zip.

## Running locally

Backend (requires `api/.env` with `ANTHROPIC_API_KEY`, see `api/.env.example`; also requires `npm` on `PATH`):
```
cd api
.venv/bin/uvicorn main:app --reload
```

Frontend:
```
cd ui
npm run dev
```

UI calls the API at `http://localhost:8000` (hardcoded `API_BASE` in `ui/src/App.tsx`); API allows CORS from `http://localhost:5173` only (`api/main.py`).

## Architecture

- `api/main.py` — `POST /api/migrate` validates the URL is a public `github.com` repo, clones it (shallow), calls `agent.run_migration_agent`, zips the output, returns a `download_url`. `GET /api/migrate/{job_id}/download` serves that zip. Job artifacts live under a temp dir (`WORK_DIR`) and are never cleaned up.
- `api/agent.py` — the migration engine: an agentic tool-use loop (not a single API call). Claude is given `list_dir`/`read_file` (scoped to the cloned repo via `repo:` paths and the in-progress output project via `output:` paths), `write_file` (scoped to `output:` only), and `run_command` (npm-only, cwd pinned to the output dir). The loop runs for up to `MAX_TURNS` turns, dispatching each `tool_use` block and feeding results back, until Claude stops requesting tools.
- `api/MIGRATION.md` — the system prompt / playbook the agent follows: explore the whole repo first, plan consistent store/module import paths before writing anything, write the Vite scaffold, migrate stores → other modules → components in that order, then **run `npm install` and `npm run build` itself and fix errors** before finishing. This is what actually validates the output compiles, unlike the old one-shot-per-file approach.
- `api/scaffold.py` — unused leftover from the previous non-agentic pipeline; kept in the repo but not called from `main.py`. Safe to delete once confirmed unneeded.
- `ui/src/App.tsx` — single-page UI: URL input + Migrate button, POSTs to `/api/migrate`, shows per-file status and a download link.

## Conventions to preserve

- The agent's tool sandboxing in `agent.py` (`_resolve`, `ToolRunner`) is a hard security boundary: `read_file`/`list_dir` may only resolve under `repo_dir` or `output_dir`, `write_file` may only resolve under `output_dir`, and `run_command` always executes `["npm", *parts]` — never pass through an arbitrary binary. Don't relax any of these when touching `agent.py`.
- Migration instructions live in `MIGRATION.md`, not as Python string prompts — tune the agent's behavior by editing that markdown file, not by hardcoding prompt text in `agent.py`.
- The playbook's ordering (explore → plan import paths → scaffold → stores → modules → components → build-and-fix loop) exists because migrating files independently with no shared context was the original bug (components each invented different guesses at a shared store/util's import path). Don't remove the "plan consistent paths before writing" step.

## Known limitations

- Public GitHub repos only (enforced in `main.py`'s `_validate_github_url`).
- Job directories under the OS temp dir are never cleaned up.
- Agent runs are slower and more expensive per migration than the old one-call-per-file approach (multiple Claude turns plus real `npm install`/`npm run build` calls), traded for actually validating the output builds.
- No automated tests exist for `agent.py`; verification has been manual (sandboxing checks + running a real repo through the endpoint).
