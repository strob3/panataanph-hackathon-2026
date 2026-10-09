# PanataanPH

A verified directory of Philippine relief drives and fundraisers, with private evidence submissions and human review.

The responsive React frontend from the downloaded PanataanPH project is integrated in `frontend/`. It uses Vite, TypeScript, and Tailwind CSS. The existing SQLAlchemy models and SQLite database remain in `src/backend/` and `data/panataanph.db`.

## Run locally

Use Python 3.10+ and Node.js 20.19+ or 22.12+. Run these commands from the repository root.

Backend setup (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

If `python` selects an unintended installation, use an explicit Python executable path for the first command. Activation is optional.

Frontend, in another terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open **http://127.0.0.1:5173**. API documentation is at **http://127.0.0.1:8000/docs**. Vite proxies `/api` requests to the local backend. `npm.cmd` avoids PowerShell's script execution policy restrictions; other shells can use `npm`.

On macOS/Linux, use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

## Integrated workflows

- `/`: responsive landing page; its evidence illustration is labeled as an example.
- `/campaigns`: verified campaigns from SQLite, with search, location, cause, urgency, and pagination.
- `/campaigns/:public_id`: public campaign details, recorded evidence score and criterion values, and a downloadable public JSON report.
- `/verify`: organizer submission form with up to four PDF/JPG/PNG documents, each at most 10 MB. The backend checks extensions, MIME types, and file signatures, generates storage filenames, and saves files privately in `storage/`.
- `/verify/report`: confirmation of the current session's saved submission and reference number. Save the reference before refreshing; private submission lookup is not exposed publicly.

Submissions remain `pending` and are excluded from the public directory. Uploaded documents, organizer contact details, registration numbers, and reviewer notes are never returned by public campaign endpoints. Donation payment details are public after approval, as explained in the form.

Automatic OCR, Ollama extraction, deterministic score computation, and the authenticated admin review UI are still planned. The imported prototype's simulated analysis and fabricated reports have been replaced with real submission confirmation; this integration never approves campaigns or generates scores automatically. No document data is sent to external AI services. The frontend has no external font dependency.

The included database and `backend.seed` contain fictional demonstration data. Existing scores are displayed as stored; do not treat demo campaigns as real donation opportunities. To start with an empty database, set `PANATAANPH_DB_PATH` to a new file before starting the backend. Do not delete the included database to reset your environment.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `PANATAANPH_DB_PATH` | `data/panataanph.db` | SQLite database file; inherited by the backend process |
| `PANATAANPH_STORAGE_PATH` | `storage/` | Private document directory; inherited by the backend process |
| `PANATAANPH_API_TARGET` | `http://127.0.0.1:8000` | Vite development API proxy target |

For a production frontend build, serve `frontend/dist/` with SPA fallback and proxy `/api` to FastAPI on the same origin. Keep `storage/` outside public static roots. The current API is intended for local development; deploy the authenticated admin workflow separately when implemented.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
cd frontend
npm.cmd run lint
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd test
```

Backend tests use an isolated in-memory database and temporary upload storage; they do not modify the included database. The frontend build includes strict TypeScript checking. Browser tests cover the directory, public report download, and private submission on desktop and mobile, using a copied database and private storage under ignored `.e2e/` folders. They start test servers automatically on ports 8100 and 5174; both ports must be free. Browser installation requires network access once.
