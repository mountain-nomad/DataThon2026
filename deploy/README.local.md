# Local deployment

Repository `main` is checked out in `/home/artur/video/datathon_app`. Historical workspace runs remain in their original directories. No pushes were made.

- Website: http://127.0.0.1:3000/demo-inference
- Backend: http://127.0.0.1:8000 (loopback only)
- Public URL: `local/public_url.txt`; pages show a login form; API routes require a signed session cookie.
- Login: `local/access.json` (private, ignored by Git).
- Ngrok token: `local/ngrok.yml` (private, ignored by Git).
- Backend API key: `backend/.env`; matching server-only key in `frontend/.env.local`.

```bash
./deploy/manage.sh build
./deploy/manage.sh start
./deploy/manage.sh tunnel
./deploy/manage.sh status
./deploy/manage.sh stop
```

Processes run in tmux sessions `datathon-backend`, `datathon-frontend`, `datathon-ngrok` and survive terminal disconnects. They do not automatically start after reboot. Stop only affects these sessions. Logs are in `local/logs/`.

Uploads and API results are stored in `local/data/`. Full ML runs, frames, prompts and raw model output are in `local/jobs/<job_id>/`. Nothing is automatically deleted. Each job copies the ML source/config/prompts into its own directory and links the local checkpoint at `../models/qwen38_27b`; historical run directories are never used as writable work directories. GPU stages use `../.venv/bin/python` with offline Hugging Face settings. Web dependencies use `.venv-web` and Node 22 from `local/node-runtime`.

`ANALYZER=app.analyzers.local:LocalAnalyzer`, `STORAGE_BACKEND=local`, concurrency 1. Supabase and RunPod are not used. Ngrok carries web requests, uploads and responses; video decoding and all model inference happen on this machine. This is a tunnel, not offline network transport.

The original CLI reloads the model per stage; it is not a persistent inference server. The local job and browser timeout is 30 minutes to allow the full pipeline. This does not meet the original five-minute jury budget by configuration. The adapter reports scenario completion as soon as the router writes a successful result; subsequent analysis keeps running on the GPU. It does not invent specialist verdicts for unfinished stages. A supervisor stops the ML subprocess group if the worker exits or the deadline expires.

Frontend setup used `npm ci --legacy-peer-deps` due to the upstream ESLint peer dependency conflict, plus the missing Linux native package `@tailwindcss/oxide-linux-x64-gnu@4.3.3`. Use the local Node 22 binary on PATH for subsequent installs/builds. The repository's package lock was preserved.

Validation: 24 existing ML tests and 4 local-adapter tests pass; production Next.js build and TypeScript checks pass. A real uploaded video completed all GPU stages with status done and one finding; JPEG evidence was checked locally. Public page shells require a password through the site login form. API routes return HTTP 401 without a valid session. See `local/validation_local.json`, `local/validation_public.json`, and `local/smoke_job.json` for the actual full-pipeline check job and `local/jobs/<job_id>/pipeline.log` for its logs.

Russian pages use explicit `/ru` URLs; unprefixed URLs redirect there. This fixes the recursive locale rewrite observed in the original frontend.

## Browser login

Open the public `/ru/demo-inference` URL. If ngrok shows its free-plan warning, click **Visit Site**, then sign in using `local/access.json`. Authentication uses a signed HttpOnly, SameSite=Lax cookie, secure over HTTPS, valid for 12 hours. Ngrok Basic Auth was replaced to avoid the browser authentication retry problem. If Chrome cached the previous Basic Auth state, open the link once in an incognito window.

The server reads `frontend/.env.local` explicitly via Node `--env-file`; login credentials and the session signing secret stay server-side. The upload route validates the session itself to preserve streaming. Other page/API requests are checked in Proxy. Ngrok startup runs ten local login/API tests before creating the tunnel. Run them separately with `.venv-web/bin/python deploy/test_site_login.py -q`. The old `local/traffic-policy.json` is preserved but is no longer used.

## Jury API

See [API.ru.md](API.ru.md) for the exact two-step API contract, curl examples and five-minute budget limitation. `local/api_access.json` contains the public base URL and API key. `/api/v1/analyze` and `/api/v1/jobs/{job_id}` accept `X-API-Key` without a browser session; other UI APIs still require the login cookie. The browser upload handler also accepts the signed session and injects the server key. An explicitly supplied wrong API key is always rejected.

## Types, limitations and official sources

Descriptions now preserve model limitations and add mapping-specific caveats before the final source paragraph, separated by blank lines. Sources come from the checked static legal mapping, never from generated names or URLs. For a rule with no suitable confirmed norm, the source paragraph is absent. All 70 rules are covered explicitly. See [legal_mapping_review.md](legal_mapping_review.md) for the eight typical-violation types without a direct confirmed public norm and the full rule inventory. The source verification record is in `backend/legal_source_checks.json`; downloaded reference texts stay in ignored `local/legal_research/`.

Canonical finding labels are fixed in `ml/configs/finding_types.json` and validated against their rule ID in both ML and backend. Router generation is masked to scenario class tokens. Historical model outputs are retained as originally generated; these changes apply to new jobs.
