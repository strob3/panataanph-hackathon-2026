# PanataanPH

### *Verify Before You Give*

---

## Problem

During typhoons, floods, fires, and other emergencies in the Philippines, donation drives spread rapidly through Facebook, Messenger, and other social platforms. Donors often receive nothing more than a screenshot, a QR code or GCash number, an organization name, and a short appeal asking for immediate help.

Checking whether a fundraiser is legitimate takes time — and during disasters, internet access may be unreliable. There is no centralized way for donors to inspect supporting evidence like permits, organizer identities, or payment details before deciding to give.

**PanataanPH solves this** by creating an evidence layer between social-media fundraising and the donor. Instead of:

```
Facebook Post → Donate
```

PanataanPH adds:

```
Facebook Post → Supporting Evidence → Local AI Analysis → Evidence Report → Human Decision → Donate
```

The AI doesn't say *"This campaign is a scam."* It says *"Here is what matches, what is missing, and what you should verify."*

---

## Project Name

**PanataanPH** — a transparent, verified directory of Philippine relief drives and fundraisers with local AI-powered document verification.

---

## Brief Description

PanataanPH is a web application that helps Filipino donors verify fundraising campaigns before donating. It combines **local AI document extraction** with **human-led verification** to evaluate fundraising legitimacy transparently.

Core capabilities:

- **QuickVerify** — Upload fundraiser screenshots, permits, and payment details. Local AI reads, extracts, and compares evidence directly on the host device, even offline.
- **Public Campaign Directory** — Browse, search, and filter verified relief drives by location, cause, and urgency.
- **Transparent Evidence Scoring** — A documented 100-point evidence-completeness score with visible breakdown — not a fraud prediction.
- **Human-in-the-Loop Review** — AI assists; authorized human reviewers make all final verification decisions.
- **Privacy-First** — All AI inference and OCR run locally. Sensitive documents are never sent to external cloud AI APIs.

---

## Why Local AI?

This is the core differentiator and directly addresses the hackathon challenge:

| Advantage | Description |
|---|---|
| **Offline Use** | Verification works when internet is weak or unavailable during a disaster |
| **Privacy** | Sensitive documents and payment info never leave the user's device/host |
| **Speed & Cost** | OCR and AI analysis happen locally — no API call per document |

> The core Local AI functionality does not depend on any cloud API. Remote hosting and authentication are secondary components.

---

## Tools

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS | Public pages, organizer workflows, admin interface |
| Backend | FastAPI, Python 3.10+ | API, authentication, campaign workflows, evidence processing |
| Database | SQLite, SQLAlchemy | Campaign records, accounts, review history |
| OCR | `pypdf` + PaddleOCR | Local text extraction from PDFs, scans, and images |
| Local AI Runtime | Ollama | Run the language model locally |
| Testing | pytest, Playwright | Backend tests, browser workflow checks |
| Version Control | Git + GitHub | Collaboration and source control |
| Containerization | Docker, Docker Compose | Deployment with persistent storage mounts |

---

## Models

| Model | Runtime | Purpose |
|---|---|---|
| **Qwen3 4B** (`qwen3:4b`) | Ollama (local) | Document classification, structured field extraction, evidence comparison |

The LLM's job is to understand OCR text and return structured information:

```json
{
  "organization": "Bayanihan Relief Foundation",
  "permit_number": "DSWD-NCR-2026-00123",
  "payment_recipient": "Juan Dela Cruz",
  "beneficiary": "Families affected by Typhoon X",
  "location": "Quezon City"
}
```

**AI Guardrails:**
- LLM extracts structured fields — it must return `null` for missing or unreadable fields, never hallucinate.
- LLM does **not** decide campaign legitimacy or predict fraud.
- Verification scores are computed by deterministic Python logic (`services/scoring.py`), never by LLM prompts.

---

## Assets

### Project Structure

```text
PanataanPH/
├── frontend/              # React, Vite, TypeScript, Tailwind
├── src/
│   └── backend/           # FastAPI application and account management
├── data/
│   └── panataanph.db      # SQLite demo database
├── storage/               # Private uploaded documents (git-ignored)
├── tests/                 # Backend and browser tests
├── scripts/               # Utility and extraction test scripts
├── docs/                  # Documentation
├── dev.bat / dev.sh       # One-click development startup
├── test_extraction.bat/sh # Extraction pipeline test
├── Dockerfile             # Container build
├── docker-compose.yml     # Production deployment
├── requirements-dev.txt   # Python dependencies
└── README.md
```

### Key Pages

| Page | Route | Description |
|---|---|---|
| Landing | `/` | Responsive homepage with evidence illustration |
| Campaign Directory | `/campaigns` | Search & filter with pagination |
| Campaign Detail | `/campaigns/:public_id` | Score breakdown, evidence, downloadable JSON report |
| About | `/about` | Evidence completeness, privacy, human review explained |
| Register / Login | `/register`, `/login` | Organizer authentication |
| Submit Campaign | `/verify` | Campaign submission with document uploads |
| My Campaigns | `/my-campaigns` | Organizer dashboard, feedback, fund reports |
| Admin Dashboard | `/admin` | Review queue, document access, decisions, audit history |

---

## Evidence Score

A transparent, rules-based 100-point score measuring **evidence completeness** — not a prediction of fraud:

| Criterion | Weight |
|---|---:|
| Applicable authorizations confirmed against evidence | 30 |
| Organizer identity verified against evidence | 20 |
| Donation details confirmed as consistent by a reviewer | 20 |
| Campaign information completeness | 20 |
| Reviewed campaign history | 10 |
| **Total** | **100** |

> *"The score represents the amount of supporting evidence available. It does not represent the probability that a fundraiser is legitimate."*

A score of **80/100 or higher** makes a campaign eligible for human approval. Scores never publish campaigns automatically.

---

Uploaded documents, organizer contact details, registration numbers, extraction results, and reviewer notes remain private. Only a designated donation QR image is published after approval. No document data is sent to external AI services. Supporting documents are extracted locally in the background after submission or additional-evidence upload. Reviewers can inspect extracted text, failure notes, and retry extraction from the admin document panel. Manual verification works without AI. The frontend has no external font dependency.

## Local document extraction

Selectable PDFs work with the base requirements. Images and scanned PDFs require the local CPU OCR packages and an initial model download:

```powershell
.\.venv\Scripts\python.exe -m pip install -r src/backend/requirements-ocr.txt
.\.venv\Scripts\python.exe scripts/check_ocr.py
ollama pull qwen3:4b
```

The check uses synthetic images, warms PaddleOCR models, and verifies both image and multi-page scanned-PDF extraction. Restart the backend after installation. Once models are cached, OCR runs offline. Run Ollama locally for structured field extraction; when unavailable, extracted text is still saved and missing fields remain null. Unreadable documents and missing OCR dependencies are recorded as failed with a reviewer-visible reason. QR donation images are separate from private evidence and are not processed as evidence.
## Campaign Lifecycle

```
pending → under_review → verified
                       → needs_information (organizer uploads more evidence → back to under_review)
                       → rejected
```

Only authorized human reviewers can grant or revoke verified status. All decisions are recorded in the audit trail.

---

## Quick Start

### Windows

```powershell
.\dev.bat
```

### macOS / Linux

```bash
chmod +x dev.sh
./dev.sh
```

### Local URLs

| Service | URL |
|---|---|
| Frontend | http://127.0.0.1:5173 |
| Backend API Docs | http://127.0.0.1:8000/docs |

### Local AI Setup

```bash
# 1. Install Ollama from https://ollama.com
# 2. Download the model
ollama pull qwen3:4b
# 3. Start the service
ollama serve
```

---

## Manual Setup

### Backend

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .\.venv\Scripts\activate         # Windows
pip install -r requirements-dev.txt
uvicorn backend.main:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

---

## Testing

```bash
# Backend tests
.venv/bin/python -m pytest tests/ -v

# Frontend lint + build
cd frontend && npm run lint && npm run build

# Browser tests (Playwright)
cd frontend && npx playwright install chromium && npm test
```

---

## Docker Deployment

```bash
docker compose up -d
```

Persistent mounts: `./data` → `/app/data` (database), `./storage` → `/app/storage` (private documents).

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PANATAANPH_DB_PATH` | `data/panataanph.db` | SQLite database file |
| `PANATAANPH_STORAGE_PATH` | `storage/` | Private document storage |
| `PANATAANPH_API_TARGET` | `http://127.0.0.1:8000` | Vite dev API proxy target |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen3:4b` | Local LLM model |
| `PANATAANPH_ALLOWED_ORIGINS` | *(empty)* | CORS allowed origins |

---

## Limitations

PanataanPH improves transparency and supports human review — it does not certify campaigns as risk-free.

- AI extraction may be incorrect or incomplete.
- Document text extraction does not prove authenticity.
- Scores reflect evidence criteria, not fraud prediction.
- Fund reports are reviewed organizer submissions, not automatic financial reconciliation.
- Privacy depends on actual deployment, access controls, and operational practices.

---

## Team

*PanataanPH Hackathon Team — AppBuilders Hackathon 2026*

## License

MIT
