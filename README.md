# PanataanPH

**A transparent directory of Philippine relief drives and fundraisers, with private evidence submissions and human-led verification.**

PanataanPH helps people explore fundraising campaigns, review available supporting evidence, and understand how campaign verification decisions are made. Organizers can submit campaigns and supporting documents for review, while authorized administrators evaluate evidence, manage campaign status, and approve reported fund activity.

The project combines a responsive React frontend, a FastAPI backend, SQLite persistence, private document storage, and optional local AI-assisted document extraction.

## Key Features

- **Public campaign directory:** Search campaigns by location, cause, and urgency, with pagination.
- **Private evidence submissions:** Organizers can submit supporting documents that are not intended for public display.
- **AI-assisted extraction:** OCR and a locally running Ollama model can extract document text and structured fields for reviewer assistance.
- **Transparent verification scores:** Documented criteria explain evidence completeness and review requirements.
- **Human-led approval:** Campaigns are never published automatically based on their scores.
- **Role-based access:** Organizer and admin/LGU reviewer accounts have separate permissions.
- **Community reporting:** Users can report campaign concerns for administrative review.
- **Fund transparency:** Organizers report received and spent funds, and administrators review entries before they affect public totals.
- **Audit and review history:** Review decisions and relevant changes are recorded for accountability.

## Architecture

The project contains a React frontend and a Python backend:

| Component | Technology | Responsibility |
|---|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS | Public pages, organizer workflows, and admin interface |
| Backend | FastAPI, Python | Authentication, campaign workflows, evidence processing, and API endpoints |
| Database | SQLite, SQLAlchemy | Campaign records, accounts, review history, and related data |
| Document storage | Private filesystem directory | Uploaded supporting documents |
| Text extraction | `pypdf` and configured OCR components | Extract text from submitted documents |
| Local AI | Ollama with `qwen3:4b` | Assist with document classification and structured field extraction |
| Testing | pytest, frontend lint/build, Playwright | Backend, frontend, and browser workflow checks |

### Hosting and data flow

The frontend can be deployed on Vercel. The FastAPI backend, database, private document storage, and Ollama runtime must be available on the backend host used by the deployed application.

**Local AI means that inference runs on the machine hosting the configured Ollama service. It does not mean that documents are processed on each organizer's device.**

In local development, documents can be stored and processed on the developer's machine. In production, documents are transmitted to the configured backend or storage service according to the application's upload flow.

For a deployment that keeps document contents off Vercel, the browser must upload documents directly to an appropriately secured backend or private storage endpoint, rather than sending them through a Vercel function that receives the file.

The frontend, backend, and AI runtime are separate components. A deployed frontend does not automatically provide access to a developer's local database or Ollama service.

## Requirements

For local development, install:

- Python and pip
- Node.js and npm
- Git
- Ollama, if testing AI-assisted extraction

Use a Python version compatible with the dependencies in `requirements-dev.txt`.

The repository includes a Vite frontend under `frontend/`, the backend source under `src/backend/`, and a SQLite database at `data/panataanph.db`.

## Quick Start

The repository includes scripts to simplify local startup.

### Windows

Double-click `dev.bat` or run:

```powershell
.\dev.bat
```

The script is intended to prepare the virtual environment, install required dependencies, start the backend and frontend, and open the application in a browser.

### macOS and Linux

```bash
chmod +x dev.sh
./dev.sh
```

The script is intended to start the local application.

Review the scripts if you need to confirm their exact startup behavior or troubleshoot an environment-specific issue.

### Local URLs

| Service | URL |
|---|---|
| Frontend | http://127.0.0.1:5173 |
| Backend API documentation | http://127.0.0.1:8000/docs |

During local development, Vite proxies `/api` requests to the FastAPI backend.

## Manual Setup

### 1. Set up the backend

From the repository root, run the following in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

If `python` selects an unintended installation, use the full path to the intended Python executable when creating the virtual environment.

Activating the virtual environment is optional when invoking its Python executable directly.

On macOS or Linux, use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

### 2. Set up the frontend

Open another terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173.

On other shells, use `npm` instead of `npm.cmd`.

## Application Workflows

### Public pages

- `/` — Responsive landing page. The evidence illustration is labeled as an example.
- `/campaigns` — Public campaign directory with search, location, cause, urgency, and pagination filters.
- `/campaigns/:public_id` — Public campaign details, recorded evidence score, criterion values, and a downloadable public JSON report.
- `/about` — Explanation of evidence completeness, privacy, and human review.

### Organizer pages

- `/register` and `/login` — Public registration and login with revocable HttpOnly cookie sessions.
- `/verify` — Authenticated campaign submission with up to four private PDF/JPG/PNG supporting documents, each up to 10 MB, plus a separate optional JPG/PNG donation QR image.
- `/verify/report` — Submission confirmation.
- `/my-campaigns` — Organizer submissions, review feedback, additional evidence uploads, and fund-report history.

Public registration does not grant administrator or LGU reviewer privileges.

### Admin and LGU reviewer pages

- `/admin` — Protected review queue, organizer account verification, private document access, extraction results, evidence checklist, campaign decisions, review history, and fund-report review.

Admin/LGU accounts can review and approve campaigns but cannot submit fundraising campaigns through the organizer workflow. Organizers must use separate organizer accounts.

## Campaign Review and Approval

New submissions begin in `pending`. A reviewer starts the review by moving a submission to `under_review`, then records one of the following outcomes:

- `needs_information`
- `verified`
- `rejected`

Reviewers must provide a reason for their decisions.

A score of **80/100 or higher makes a campaign eligible for ordinary human approval**. Scores never publish campaigns automatically.

Ordinary approval also requires:

1. A verified organizer account.
2. The applicable authorization evidence checklist.
3. Identity verification against the submitted evidence.
4. Confirmation that donation details are consistent with the supporting evidence.
5. Review and resolution of warnings and major inconsistencies.

An administrator may approve a campaign below the normal score threshold only through an explicit threshold exception with a separately recorded reason. This exception does not bypass organizer account verification or unresolved warnings. Public campaign details identify when such an exception was used.

Unapproved submissions are excluded from public campaign listings, direct public campaign details, and donation QR endpoints. Revoking organizer verification immediately hides that organizer's campaigns.

Previously verified fictional demonstration rows without an owner remain subject to the legacy score threshold. New submissions always require an authenticated owner.

### Requests for additional information

When a reviewer selects `needs_information`, the organizer can upload additional private supporting files under `/my-campaigns`.

After an upload:

- The campaign returns to `under_review`.
- Its previous score is cleared for reassessment.
- The original feedback and the organizer's response remain in review history.
- Uploading additional evidence does not approve or publish the campaign.

## Verification Score

PanataanPH uses a documented 100-point evidence-completeness score.

| Criterion | Weight |
|---|---:|
| Applicable authorizations confirmed against evidence | 30 |
| Organizer identity verified against evidence | 20 |
| Donation details confirmed as consistent by a reviewer | 20 |
| Campaign completeness | 20 |
| Reviewed campaign history | 10 |
| **Total** | **100** |

Campaign completeness awards four points for each of the following:

- Title and description
- Campaign purpose
- Location
- Beneficiaries
- Positive fundraising target

The authorization, identity, and donation-consistency criteria require the applicable reviewer checklist. A threshold exception can account for alternative evidence, but it cannot bypass organizer account verification or unresolved warnings.

The score measures evidence completeness under the documented criteria. It does not predict fraud, guarantee document authenticity, certify an organizer, or guarantee that donations will be used as intended.

AI extraction results support the review process. Reviewers remain responsible for assessing the original evidence and making campaign decisions.

## Private Documents and Privacy

Organizers may submit documents such as IDs, SEC/DTI registration records, LGU permits, authorization letters, bank or e-wallet evidence, and other relevant supporting materials.

Uploaded documents, organizer contact details, registration numbers, extraction results, and reviewer notes are intended to remain private. Only a designated donation QR image is published after campaign approval, according to the application's configured workflow.

The application should restrict access to private documents to authorized users, keep private storage outside public static directories, and avoid exposing sensitive information through public APIs, logs, or downloadable reports.

### Local AI processing

PanataanPH supports local document extraction using OCR components and Ollama with the `qwen3:4b` model.

The intended design does not send document contents to third-party cloud AI APIs for extraction. Actual privacy depends on the configured upload path, backend host, storage, logs, and any other services involved.

Once the required software and model are installed, extraction can operate without an external AI API, provided the backend and local model are available. The entire web application is not necessarily offline: remote users still need connectivity to reach the hosted website and backend.

The model may make extraction mistakes or return unsupported values. Missing fields should be represented as `null` where supported by the extraction pipeline, and material fields must be checked against the original documents by an authorized reviewer.

If Ollama is unavailable, the backend is designed to fall back to text extraction where supported. Manual review can continue without AI extraction.

The frontend does not require an external font dependency.

## Local AI Setup

Only the backend host or developer performing local AI testing needs to install Ollama. Donors and organizers use the browser and do not need to clone the repository or install the model.

### 1. Install Ollama

Download and install Ollama from [ollama.com](https://ollama.com).

### 2. Download the model

```bash
ollama pull qwen3:4b
```

### 3. Start the Ollama service

```bash
ollama serve
```

If the Ollama desktop application already starts the service, a separate `ollama serve` process may not be necessary.

The default API endpoint is `http://127.0.0.1:11434`.

### 4. Test extraction

Windows:

```powershell
.\test_extraction.bat
```

macOS/Linux:

```bash
chmod +x test_extraction.sh
./test_extraction.sh
```

The extraction pipeline uses the local Ollama service when it is configured and available.

PDF text extraction uses `pypdf` for selectable text. OCR support for scanned PDFs and images depends on the OCR components implemented and configured in the repository.

## Set Up an Admin or LGU Reviewer

No default privileged credentials are provided. An authorized project operator must provision reviewer accounts locally.

The following PowerShell commands assume the virtual environment has already been created and dependencies installed.

### Create an LGU reviewer

```powershell
cd src
..\.venv\Scripts\python.exe -m backend.manage_accounts create --email reviewer@example.com --name "Authorized Reviewer" --role lgu
cd ..
```

Use `--role admin` for a project administrator.

The command prompts for a password. It does not promote an existing public registration.

### Reset an existing reviewer account

If an account was registered incorrectly, repair it explicitly:

```powershell
cd src
..\.venv\Scripts\python.exe -m backend.manage_accounts reset --email reviewer@example.com --name "Authorized Reviewer" --role lgu
cd ..
```

This resets the password, marks the account verified, assigns the selected reviewer role, and revokes existing sessions for that account.

### Security controls

- Passwords are hashed using scrypt.
- Session tokens are hashed in SQLite.
- State-changing cookie-authenticated requests enforce the same-origin policy.
- Account verification and campaign decisions record reviewer identity and a reason.
- Vite preserves the frontend `Host` header when proxying in local development.

### Recommended review order

1. Inspect submitted documents and the donation destination.
2. Verify the organizer's account.
3. Start the campaign review.
4. Complete the evidence checklist and investigate warnings.
5. Record the decision and reason.
6. Review submitted fund reports separately after campaign approval.

## Fund Transparency

Organizers can report received and spent funds under `/my-campaigns`. Each report requires administrator approval before it affects public totals.

Fund amounts are stored as integer PHP centavos to avoid floating-point rounding errors.

Public campaign pages display:

- Approved received funds
- Approved spent funds
- Remaining balance
- Progress toward the fundraising target
- Approved dated fund-report entries

A zero total means no approved reports have been recorded; it does not prove that no donations or expenses occurred.

These are reviewed organizer reports, not automatic payment reconciliation or independent confirmation of bank transactions. Donations occur through the organizer's payment provider.

## Database and Demo Data

Startup applies the documented account, session, QR, fund-report, and audit table changes, along with a nullable campaign ownership column, to existing databases without intentionally deleting campaign records.

The included database and `backend.seed` contain fictional demonstration data. Existing scores are displayed as stored.

**Do not treat fictional demo campaigns as real donation opportunities.**

To start with an empty database, set `PANATAANPH_DB_PATH` to a new database file before starting the backend. Do not delete the included database merely to reset your environment.

For production, use persistent storage for the database and establish a backup and recovery procedure. Container filesystems may be ephemeral, so a persistent volume or suitable database service must be configured.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PANATAANPH_DB_PATH` | `data/panataanph.db` | SQLite database file |
| `PANATAANPH_STORAGE_PATH` | `storage/` | Private document storage directory |
| `PANATAANPH_API_TARGET` | `http://127.0.0.1:8000` | Vite development API proxy target |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen3:4b` | Local LLM model used for extraction |
| `PANATAANPH_ALLOWED_ORIGINS` | Empty string | Comma-separated allowed origins for CORS |

The database and storage paths must be writable by the backend process. Protect them with appropriate filesystem permissions.

The Ollama endpoint must be reachable from the backend host. In a remote deployment, `127.0.0.1` refers to the backend host itself, not the browser or developer's computer.

For production, serve `frontend/dist/` using an appropriate web server with SPA fallback and route API requests to FastAPI on the configured backend. Keep `storage/` outside public static roots, and enforce server-side authorization for private documents.

Local HTTP sessions use SameSite and HttpOnly cookie settings; HTTPS sessions also use Secure cookies, according to the configured application behavior.

CORS restricts browser access from disallowed origins but is not a replacement for authentication, authorization, or CSRF protections.

## Docker Deployment

The repository provides a Docker Compose configuration for running the backend with persistent database and private document storage mounts.

Start the configured services with:

```bash
docker compose up -d
```

The documented mounts are:

- `./data` → `/app/data` for the database.
- `./storage` → `/app/storage` for private documents.

For a Vercel frontend deployment, configure `frontend/vercel.json` to route `/api/:path*` requests to the intended hosted backend.

Before deploying, confirm that the backend is reachable over HTTPS, persistent storage is configured, the required environment variables are set, and private document endpoints require authorization. The backend and Ollama runtime must be deployed separately from Vercel unless a compatible service is explicitly configured for them.

Do not expose Ollama's API publicly without appropriate network restrictions and security controls.

## Testing and Verification

Run the backend tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

Run frontend linting and the production build:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

Install Playwright's Chromium browser if needed:

```powershell
npx.cmd playwright install chromium
```

Run the frontend tests:

```powershell
npm.cmd test
```

Use `npm` instead of `npm.cmd` in shells that do not require the Windows command wrapper.

### Test coverage

The documented browser tests cover:

- Signup, login, and logout
- Campaign submissions
- Reviewer approval
- Donation QR behavior
- Fund transparency
- Responsive layouts at 320, 375, 768, and 1280 pixels

Backend tests use an isolated in-memory database and temporary upload storage. Browser tests use a copied database and private storage under ignored `.e2e/` directories, and provision a fictional reviewer only in that disposable database.

Test servers start automatically on ports `8100` and `5174`. Both ports must be available. Installing the browser requires network access the first time.

## Project Structure

```text
PanataanPH/
├── frontend/            # React, Vite, TypeScript, Tailwind
├── src/
│   └── backend/         # FastAPI application and account management
├── data/
│   └── panataanph.db    # Included SQLite demo database
├── storage/             # Private uploaded documents
├── tests/               # Backend tests
├── dev.bat              # Windows development startup
├── dev.sh               # macOS/Linux development startup
├── test_extraction.bat  # Windows extraction test
├── test_extraction.sh   # macOS/Linux extraction test
├── requirements-dev.txt
└── README.md
```

The actual repository may contain additional files and configuration.

## Limitations

PanataanPH is intended to improve transparency and support human review, not to certify fundraising campaigns as risk-free.

- AI extraction may be incorrect or incomplete.
- Document text extraction does not prove authenticity.
- Scores reflect documented evidence criteria, not a prediction of fraud.
- Fund reports are subject to review and are not automatic financial reconciliation.
- Privacy and security depend on the actual deployment, access controls, storage configuration, and operational practices.

Reviewers and donors should assess available evidence independently.

## License and Contact

Add the project's chosen license and official contact information here before public release.
