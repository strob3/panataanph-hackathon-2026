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
- `/register` and `/login`: local organizer accounts and revocable HttpOnly cookie sessions. Public registration never grants admin/LGU privileges.
- `/verify`: login required; organizer submission with up to four private PDF/JPG/PNG documents and a separate optional donation QR image (JPG/PNG), each at most 10 MB. QR label and donation details become public only after approval.
- `/verify/report`: submission confirmation. `/my-campaigns` shows the signed-in organizer's submissions, review feedback, and fund-report history.
- `/admin`: protected admin/LGU queue, organizer account verification, private documents and extraction results, evidence checklist, campaign decisions and review history, and fund-report review.
- `/about`: consistent responsive explanation of privacy, evidence completeness, and human review.

Reviewer accounts follow separation of duties: admin/LGU accounts can review and approve campaigns but cannot submit fundraising campaigns. Organizers submit campaigns through separate organizer accounts.

Submissions remain `pending` until a reviewer starts `under_review`, then selects `needs_information`, `verified`, or `rejected` with a reason. **80/100 makes a campaign eligible for human approval; scores never publish campaigns automatically.** Approval also requires a verified organizer account and explicit confirmation that warnings and major inconsistencies have been reviewed and resolved. An admin can approve a lower score only through an explicit threshold exception with a separate recorded reason. Public details identify this exception. Unapproved submissions are excluded from lists, direct public details, and donation QR endpoints. Revoking organizer verification hides that organizer's campaigns immediately. Previously verified fictional demo rows without an owner remain readable only if they meet the score threshold; new submissions always have an authenticated owner.

When reviewers request additional evidence, organizers upload private supporting files under `/my-campaigns`. The campaign returns to `under_review`, its previous score is cleared, and the original feedback and response remain in review history. Uploads never approve or publish a campaign.

Score rules use the documented 30/20/20/20/10 weights: applicable authorizations confirmed against evidence (30), verified organizer identity confirmed against evidence (20), matching donation details confirmed by reviewer (20), campaign completeness (4 points each for title/description, purpose, location, beneficiaries, and positive target; 20 total), and reviewed campaign history (10). Ordinary approval requires the authorizations, identity, and payment consistency checklist; an audited threshold exception can account for alternative evidence but cannot bypass account verification or unresolved warnings. The score measures evidence completeness; it does not predict fraud or guarantee authenticity.

Uploaded documents, organizer contact details, registration numbers, extraction results, and reviewer notes remain private. Only a designated donation QR image is published after approval. No document data is sent to external AI services. Supporting documents are extracted locally in the background after submission or additional-evidence upload. Reviewers can inspect extracted text, failure notes, and retry extraction from the admin document panel. Manual verification works without AI. The frontend has no external font dependency.

## Local document extraction

Selectable PDFs work with the base requirements. Images and scanned PDFs require the local CPU OCR packages and an initial model download:

```powershell
.\.venv\Scripts\python.exe -m pip install -r src/backend/requirements-ocr.txt
.\.venv\Scripts\python.exe scripts/check_ocr.py
ollama pull qwen3:4b
```

The check uses synthetic images, warms PaddleOCR models, and verifies both image and multi-page scanned-PDF extraction. Restart the backend after installation. Once models are cached, OCR runs offline. Run Ollama locally for structured field extraction; when unavailable, extracted text is still saved and missing fields remain null. Unreadable documents and missing OCR dependencies are recorded as failed with a reviewer-visible reason. QR donation images are separate from private evidence and are not processed as evidence.

Organizers report received/spent funds under `/my-campaigns`. Every entry needs admin approval before affecting public totals. PHP values are stored as integer centavos. Public pages show received, spent, balance, target progress, and approved dated entries. These are reviewed organizer reports, not automatic payment reconciliation; zero means no approved reports. Donations happen through the organizer's payment provider.

## Set up an admin or LGU reviewer

No default privileged credentials exist. Provision authorized reviewers locally, choose a password when prompted, then log in at `/login` and open `/admin`:

```powershell
cd src
..\.venv\Scripts\python.exe -m backend.manage_accounts create --email reviewer@example.com --name "Authorized Reviewer" --role lgu
cd ..
```

Use `--role admin` for a project administrator. The command never promotes existing public registrations. Passwords are hashed with scrypt; session tokens are hashed in SQLite. Account verification and campaign decisions record reviewer identity and reason. State-changing cookie requests enforce the same origin; Vite preserves the frontend Host header when proxying.

If the email already exists because it was registered incorrectly, repair it explicitly:

```powershell
cd src
..\.venv\Scripts\python.exe -m backend.manage_accounts reset --email reviewer@example.com --name "Authorized Reviewer" --role lgu
cd ..
```

This resets the password, marks the account verified, assigns the selected reviewer role, and revokes its existing sessions.

Review order: inspect submission documents and donation destination, verify organizer account, start campaign review, confirm evidence checklist, and save the final decision. A verified campaign's fund reports then appear in the same admin detail for separate approval.

Startup adds account/session/QR/fund/audit tables and a nullable campaign ownership column to existing databases without deleting campaigns.

The included database and `backend.seed` contain fictional demonstration data. Existing scores are displayed as stored; do not treat demo campaigns as real donation opportunities. To start with an empty database, set `PANATAANPH_DB_PATH` to a new file before starting the backend. Do not delete the included database to reset your environment.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `PANATAANPH_DB_PATH` | `data/panataanph.db` | SQLite database file; inherited by the backend process |
| `PANATAANPH_STORAGE_PATH` | `storage/` | Private document directory; inherited by the backend process |
| `PANATAANPH_API_TARGET` | `http://127.0.0.1:8000` | Vite development API proxy target |

For a production frontend build, serve `frontend/dist/` with SPA fallback and proxy `/api` to FastAPI on the same origin, preserving the frontend Host and scheme. Keep `storage/` outside public static roots. Local HTTP sessions use SameSite/HttpOnly; HTTPS sessions also use Secure cookies.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
cd frontend
npm.cmd run lint
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd test
```

Backend tests use an isolated in-memory database and temporary upload storage; they do not modify the included database. The frontend build includes strict TypeScript checking. Browser tests cover signup/login/logout, submissions, reviewer approval, donation QR, fund transparency, and layouts at 320/375/768/1280px on desktop/mobile. They use a copied database and private storage under ignored `.e2e/` folders, and provision a fictional reviewer only in that disposable database. Test servers start automatically on ports 8100 and 5174; both ports must be free. Browser installation requires network access once.
