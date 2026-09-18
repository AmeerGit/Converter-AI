# Converter-AI

Converter-AI migrates a public Vue 3 GitHub repository into a runnable React
18 + TypeScript + Vite project.

## Local development

Create `api/.env` from `api/.env.example` and set `ANTHROPIC_API_KEY`.

Start the API:

```bash
cd api
.venv/bin/uvicorn main:app --reload
```

Start the UI in a second terminal:

```bash
cd ui
npm run dev
```

The UI uses `http://localhost:8000` by default. Set
`VITE_API_BASE_URL` in `ui/.env.local` when using another API URL.

## Free deployment on Render

Render hosts both parts as separate services from the same repository:

- **Static Site**: builds and serves the React/Vite UI.
- **Web Service**: runs the Python FastAPI API. A web service is required
  because a migration performs a Git clone, multiple Claude requests,
  `npm install`, `npm run build`, filesystem work, and ZIP creation in one
  request.

The committed `render.yaml` defines both services.

### Create the Render services

1. Create a Render account and connect GitHub.
2. Select **New > Blueprint** and choose this repository.
3. Review the two services from `render.yaml`:
   - `converter-ai-ui` — Static Site, root `ui`.
   - `converter-ai-api` — Python Web Service, root `api`.
4. Create the services using the free plan where available.

If creating them manually, use:

Static Site:

```text
Root directory: ui
Build command: npm ci && npm run build
Publish directory: dist
```

Web Service:

```text
Root directory: api
Build command: pip install -r requirements.txt
Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Configure service environment variables

On the API service, add:

```text
ANTHROPIC_API_KEY=your-real-anthropic-api-key
FRONTEND_URL=https://converter-ai-ui.onrender.com
```

On the Static Site, add this build-time variable:

```text
VITE_API_BASE_URL=https://converter-ai-api.onrender.com
```

Replace both example hostnames with the actual Render URLs. Do not put
`ANTHROPIC_API_KEY` in the Static Site or in any `VITE_*` variable.

After deployment, verify:

```text
https://<api-service>.onrender.com/healthz
```

returns:

```json
{"status":"ok"}
```

Then open the Static Site URL and run a small migration.

## GitHub Actions CI/CD

The workflows in `.github/workflows/`:

- Run the frontend install and production build on pull requests and pushes
  to `main`.
- Install the backend dependencies and compile all Python files on the same
  events.
- Trigger both Render deploy hooks after a successful `main` build.

For GitHub Actions-triggered deployments, add these GitHub repository secrets:

- `RENDER_UI_DEPLOY_HOOK_URL`
- `RENDER_API_DEPLOY_HOOK_URL`

Both secrets are optional when both Render services are configured with native
Git auto-deploy from `main`. The workflows never require or expose
`ANTHROPIC_API_KEY`.

## Free-tier limitations

The migration endpoint is synchronous. A request remains open during cloning,
Claude calls, dependency installation, and the output build. Free services may
sleep when idle, enforce request/time or memory limits, and limit monthly
usage. Generated ZIP files are stored in the backend's temporary filesystem
and can disappear when the service restarts; durable object storage would be
needed for permanent downloads.