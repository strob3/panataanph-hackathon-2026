# PanataanPH Implementation Plan

**Project:** PanataanPH  
**Duration:** 24-hour hackathon  
**Architecture:** Local AI document extraction with human-led verification

## 1. Technology Stack

| Component | Technology | Responsibility |
|---|---|---|
| Frontend | React/Vite, TypeScript, Tailwind CSS | Integrated responsive directory, submission forms, admin dashboard |
| Backend | Python, FastAPI | API endpoints and processing orchestration |
| OCR | PaddleOCR | Extract text from scanned documents and images |
| PDF parsing | PDF text extraction library | Extract selectable text from text-based PDFs |
| Local LLM runtime | Ollama | Run the LLM locally |
| LLM | Qwen3 4B | Interpret extracted text and return structured JSON |
| Database | SQLite | Store campaigns, document metadata, findings, and review history |
| File storage | Local filesystem | Store uploaded documents privately |

All core services run on the same host machine during the hackathon demonstration. Uploaded documents must not be sent to external AI APIs.

## 2. Implementation Phases

| Phase | Description | Time |
|---|---|---:|
| 1 | Project setup and architecture | 2 hours |
| 2 | Public campaign directory | 3 hours |
| 3 | Campaign submission and document uploads | 3 hours |
| 4 | Local AI document extraction | 5 hours |
| 5 | Data validation and verification score | 3 hours |
| 6 | Admin review dashboard | 3 hours |
| 7 | Integration and offline testing | 3 hours |
| 8 | Contingency buffer | 2 hours |
| **Total** | | **24 hours** |

## Current implementation

Organizer signup/login, authenticated submissions, private evidence, optional donation QR images, admin/LGU account and campaign review, deterministic scores, review history, and approved fund-report transparency are implemented. Score ≥80 qualifies a campaign for human approval; publication never happens automatically. Approval requires a verified organizer account and confirmed resolution of warnings and major inconsistencies. Below-threshold approval requires an explicit exception and separate recorded reason. Organizers can respond to evidence requests with private uploads; this resets scoring and returns the campaign to human review. Layout checks cover 320/375/768/1280px and a consistent About page.

Scores follow the 30/20/20/20/10 criteria below, using explicit reviewer evidence confirmations and deterministic campaign completeness. OCR/Ollama remains pending; existing extraction data can be inspected, and manual review works offline without an inference service. Fund totals are reviewed organizer reports rather than automatically reconciled payment transactions.

See README.md for account provisioning, endpoints, and runnable checks. WORKFLOW.md remains the branch/PR/review process.

## Phase 1: Project Setup and Architecture

**Duration: 2 hours**

### Tasks

- [ ] Initialize the Next.js frontend with TypeScript and Tailwind CSS.
- [ ] Create the FastAPI backend.
- [ ] Set up SQLite and database initialization or migrations.
- [ ] Install PaddleOCR and its required dependencies.
- [ ] Install Ollama and download the Qwen3 4B model.
- [ ] Configure environment variables.
- [ ] Create private document storage.
- [ ] Establish communication between Next.js and FastAPI.
- [ ] Verify that FastAPI can communicate with Ollama.

### Suggested Project Structure

```text
panataanph/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── backend/
│   ├── routes/
│   ├── services/
│   │   ├── ocr.py
│   │   ├── llm.py
│   │   └── extraction.py
│   ├── schemas/
│   ├── database.py
│   ├── models.py
│   ├── config.py
│   └── main.py
├── storage/
│   └── .gitkeep
├── data/
│   └── .gitkeep
├── docs/
│   ├── PROJECT_CONTEXT.md
│   └── IMPLEMENTATION.md
├── .gitignore
├── .env.example
└── README.md
```

The actual upload directory and database file must be excluded from version control. The structure can be adjusted as implementation progresses.

**Deliverable:** The frontend, backend, database, OCR dependencies, and local model runtime are ready.

## Phase 2: Public Campaign Directory

**Duration: 3 hours**

### Tasks

- [x] Build the homepage and campaign listing.
- [x] Create reusable campaign cards.
- [x] Create individual campaign detail pages.
- [x] Display campaign purpose, organizer, location, beneficiaries, and fundraising target.
- [x] Display verification status and evidence completeness score.
- [x] Implement public search/location/cause/urgency filters and admin status filters.
- [x] Add fictional sample campaigns for development and demonstration.
- [x] Add responsive layouts and a consistent About page.
- [x] Display approved donation QR images and reviewed fund transparency.

### Requirements

- Only approved campaigns appear in the public directory.
- Campaign details must clearly distinguish organizer-provided claims from admin-reviewed information.
- Public pages must not expose private identity documents or sensitive uploads.
- Search and filtering must work with the stored campaign data.

**Deliverable:** A usable public directory backed by SQLite.

## Phase 3: Campaign Submission and Document Uploads

**Duration: 3 hours**

### Tasks

- [ ] Build a multi-step campaign submission form.
- [x] Collect organizer and organization information.
- [x] Collect campaign purpose, beneficiaries, location, target amount, and payment details.
- [x] Accept supporting PDFs and images.
- [x] Validate file types, file sizes, and required fields.
- [x] Store uploaded files in a private directory.
- [x] Save document metadata and campaign information in SQLite.
- [x] Set new campaigns to `pending`.
- [x] Require organizer login and accept private responses to evidence requests.

### Requirements

- Generate unique internal identifiers for campaigns and uploaded documents.
- Store file paths or storage keys rather than binary files directly in SQLite.
- Prevent uploaded filenames from determining filesystem paths.
- Keep private files inaccessible through unrestricted static URLs.
- Provide clear upload and processing error messages.

**Deliverable:** Organizers can submit campaigns with supporting evidence.

## Phase 4: Local AI Document Extraction

**Duration: 5 hours**

This phase implements the core Local AI functionality.

### 4.1 Document Processing Flow

1. The frontend uploads a document to FastAPI.
2. FastAPI validates and stores the document.
3. FastAPI determines whether the PDF contains selectable text.
4. A PDF parser extracts embedded text when available; PaddleOCR handles scanned PDFs and images.
5. FastAPI sends the extracted text and field instructions to Ollama.
6. Ollama runs Qwen3 4B and generates structured JSON.
7. FastAPI validates the response against a defined schema.
8. FastAPI stores the extraction results and processing status.
9. The frontend displays the results alongside the original document for admin review.

### 4.2 Define the Extraction Schema

Create a Pydantic model for extracted document information.

Suggested fields:

- `document_type`
- `issuing_authority`
- `permit_number`
- `organization_name`
- `purpose`
- `issue_date`
- `expiration_date`
- `beneficiaries`
- `missing_fields`

Fields should be optional when documents may legitimately omit them. Dates should use a consistent format, such as `YYYY-MM-DD`, when they can be interpreted reliably.

### 4.3 Implement OCR and PDF Parsing

- [ ] Implement extraction of embedded PDF text.
- [ ] Integrate PaddleOCR for scanned documents and images.
- [ ] Normalize whitespace and remove irrelevant OCR artifacts where safe.
- [ ] Handle empty or unreadable extraction results.
- [ ] Preserve the original uploaded document for comparison.
- [ ] Avoid unnecessary OCR when selectable text is already available.

### 4.4 Integrate Ollama and Qwen3

- [ ] Configure FastAPI to call Ollama's local HTTP API.
- [ ] Create a prompt for extracting only the requested fields.
- [ ] Include the OCR output as untrusted document content.
- [ ] Require missing or unsupported values to be returned as `null`.
- [ ] Use Ollama structured output with a JSON schema where supported.
- [ ] Parse and validate the generated response using Pydantic.
- [ ] Handle timeouts, invalid output, and model errors.
- [ ] Store the results for admin review.

Example extraction instructions:

> Extract the requested fields from the supplied document text. Use only information supported by the text. Return null for missing or unreadable values. Do not invent details. Do not determine whether the document is authentic, whether an organization is legitimate, or whether a campaign should be approved.

### 4.5 Example Output

```json
{
  "document_type": "Solicitation Permit",
  "issuing_authority": "Example Government Agency",
  "permit_number": "EX-2026-00123",
  "organization_name": "Example Relief Foundation",
  "purpose": "Typhoon Relief Operations",
  "issue_date": "2026-09-15",
  "expiration_date": "2026-12-15",
  "beneficiaries": null,
  "missing_fields": ["beneficiaries"]
}
```

This is illustrative data, not an actual permit.

### 4.6 API Endpoint

Implement an endpoint such as:

`POST /api/documents/{document_id}/extract`

It should initiate extraction for a previously uploaded document and return the processing status and extracted fields when processing completes.

**Deliverable:** Uploaded documents are processed locally and produce validated structured information.

## Phase 5: Data Validation and Verification Score

**Duration: 3 hours**

### Tasks

- [ ] Compare extracted information against campaign submission details.
- [ ] Flag missing, unreadable, or ambiguous information.
- [ ] Highlight discrepancies in organization names, permit numbers, and dates.
- [x] Implement a deterministic evidence completeness score from 0 to 100.
- [x] Show a score breakdown and explain missing points.
- [ ] Distinguish missing information from a confirmed mismatch.
- [x] Store deterministic score findings so admins can review them.

### Proposed Score Criteria

| Criterion | Maximum points |
|---|---:|
| Applicable permits or authorizations | 30 |
| Organizer identity and registration information | 20 |
| Consistency of organizer and payment details | 20 |
| Campaign information completeness | 20 |
| Previously reviewed campaign history | 10 |
| **Total** | **100** |

These weights are provisional and should be finalized during implementation.

### Scoring Rules

- Calculate the score using application code, not the LLM.
- Award points according to explicit, documented rules.
- Do not treat missing information as proof of fraud.
- Do not imply that a high score guarantees legitimacy.
- Determine applicable legal requirements separately from the score.
- Require appropriate human review for legally required permits and unresolved discrepancies.

**Deliverable:** A transparent evidence completeness score with actionable findings.

## Phase 6: Admin Review Dashboard

**Duration: 3 hours**

### Tasks

- [x] Build an admin dashboard listing pending and flagged submissions.
- [x] Display campaign information and uploaded documents.
- [x] Display stored extracted fields alongside links to original documents (automatic extraction remains pending).
- [x] Display the score breakdown and validation findings.
- [x] Allow admins to approve campaigns.
- [x] Allow admins to reject campaigns with a recorded reason.
- [x] Allow admins to request additional information.
- [x] Record review history and decisions.
- [x] Verify organizer accounts through authorized admin/LGU accounts.
- [x] Enforce 80/100 eligibility, human approval, resolved warnings, and audited threshold exceptions.
- [x] Review received/spent fund reports before publishing totals.
- [x] Implement campaign reporting and review.
- [x] Restrict access to admin routes and private documents.

### Campaign Statuses

- `pending`
- `under_review`
- `needs_information`
- `verified`
- `rejected`

Status transitions should be controlled by the backend. Public campaign listings should display only campaigns approved for publication.

Reports should trigger review, not automatically label a campaign fraudulent.

**Deliverable:** Admins can inspect evidence and make the final verification decision.

## Phase 7: Integration and Offline Testing

**Duration: 3 hours**

### End-to-End Test

- [x] Submit a fictional relief campaign.
- [x] Upload a fictional supporting permit.
- [ ] Extract text through the PDF parser or PaddleOCR.
- [ ] Send the text to Qwen3 through Ollama.
- [ ] Validate and store the returned JSON.
- [ ] Display the extracted information in the admin dashboard.
- [ ] Compare extracted fields against the campaign submission.
- [x] Calculate and display the evidence completeness score.
- [x] Approve the campaign or request additional information.
- [x] Confirm that the public campaign status updates correctly.

### Error and Security Tests

- [x] Unsupported file type.
- [x] Oversized upload.
- [ ] Empty or unreadable document.
- [x] Missing fields.
- [ ] Invalid model output.
- [ ] Model timeout or unavailable Ollama service.
- [ ] Mismatched campaign and document information.
- [x] Unauthorized access to admin routes.
- [x] Unauthorized access to private documents.

### Offline Demonstration

Before disconnecting from the internet:

1. Download the required Ollama model.
2. Install all application dependencies.
3. Confirm the OCR models and other required assets are available locally.
4. Start all services and test the complete workflow.

Then disconnect from the internet and process a new sample document. Verify that OCR, LLM extraction, score calculation, database operations, and admin review continue to work.

Use fictional documents and campaigns during the demonstration.

**Deliverable:** A tested end-to-end MVP that can demonstrate its core Local AI workflow offline after setup.

## Phase 8: Contingency Buffer

**Duration: 2 hours**

Reserve time for:

- Fixing integration problems.
- Addressing slow model inference.
- Correcting UI issues.
- Fixing data validation problems.
- Rehearsing the final demonstration.

Do not add major new features during the buffer unless the core workflow is already stable.

## 3. Implementation Milestones

- [ ] **Milestone 1:** FastAPI successfully communicates with Ollama.
- [ ] **Milestone 2:** PaddleOCR extracts text from a sample document.
- [ ] **Milestone 3:** Qwen3 returns valid structured JSON.
- [ ] **Milestone 4:** Extracted fields appear beside the original document in the admin interface.
- [ ] **Milestone 5:** The score and validation findings are generated deterministically.
- [ ] **Milestone 6:** Admin decisions update campaign statuses correctly.
- [ ] **Milestone 7:** The core workflow runs without internet access after setup.

## 4. Priorities

### Must Have

- Public campaign directory and detail pages.
- Campaign submission and document upload.
- Local OCR and LLM extraction.
- Structured output validation.
- Evidence completeness score.
- Admin review and status management.
- Offline demonstration.

### Should Have

- Search and filtering.
- Detailed score breakdown.
- Campaign reporting.
- Review history.
- Clear handling of unreadable documents and extraction failures.

### Defer if Time Is Limited

- Donor accounts.
- Notifications.
- Cloud deployment.
- Advanced fraud detection.
- Automatic verification against external government databases.
- Production-scale infrastructure.

## 5. Key Design Principles

1. **OCR extracts text; the LLM structures it.** The model must not invent missing information.
2. **FastAPI coordinates processing.** It receives files, invokes parsing and OCR, calls Ollama, validates output, and returns results.
3. **Scoring is deterministic.** Application logic calculates the score using documented rules.
4. **Admins make the final decision.** AI findings assist the review process but do not establish authenticity or fraud.
5. **Documents remain private.** Public pages expose only information approved for publication.
6. **Local inference is demonstrated honestly.** The model runs on the host machine, not necessarily on each donor's device.
7. **Offline capability is tested.** The core workflow must work without external AI services or internet access after dependencies and models are installed.

## 6. Definition of Done

The MVP is complete when a fictional campaign can be submitted with supporting documents, processed through local text extraction and LLM inference, displayed with structured fields, evaluated by deterministic scoring rules, and reviewed by an admin. The resulting campaign status must update correctly, private documents must remain protected, and the core workflow must operate offline after initial setup and model downloads.
