"""End-to-end test script for document submission and AI extraction pipeline."""

import io
import json
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx
from fastapi.testclient import TestClient
from backend import main
from backend.services import llm

SAMPLE_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 280 >>
stream
BT
/F1 12 Tf
72 712 Td
(REPUBLIC OF THE PHILIPPINES) Tj
0 -20 Td
(DEPARTMENT OF SOCIAL WELFARE AND DEVELOPMENT) Tj
0 -20 Td
(SOLICITATION PERMIT: DSWD-SB-SP-00123-2026) Tj
0 -20 Td
(ORGANIZATION: Tulong Kabataan Foundation) Tj
0 -20 Td
(PURPOSE: Typhoon Relief Aid and Family Food Packs) Tj
0 -20 Td
(ISSUE DATE: 2026-09-15) Tj
0 -20 Td
(VALID UNTIL: 2026-12-15) Tj
0 -20 Td
(BENEFICIARIES: Displaced Families in Marikina) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000117 00000 n 
0000000244 00000 n 
0000000576 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
651
%%EOF
"""


def check_ollama() -> bool:
    try:
        r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def main_test():
    print("=" * 60)
    print("PanataanPH - Local AI Document Extraction E2E Test")
    print("=" * 60)

    ollama_online = check_ollama()
    if ollama_online:
        print("[✓] Ollama daemon is ONLINE (http://127.0.0.1:11434)")
    else:
        print("[!] Ollama daemon is OFFLINE (Testing graceful offline fallback)")

    from backend.database import init_db
    init_db()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_storage = Path(tmp_dir) / "storage"
        tmp_storage.mkdir(parents=True, exist_ok=True)
        main.STORAGE_ROOT = tmp_storage

        with TestClient(main.app) as client:
            # 1. Health check
            print("\n1. Testing API Health...")
            health_resp = client.get("/api/health")
            assert health_resp.status_code == 200
            print(f"   Response: {health_resp.json()}")

            # 2. Submit campaign with PDF permit
            print("\n2. Submitting Campaign + Sample DSWD Permit PDF...")
            campaign_payload = {
                "organizer_name": "Juan Dela Cruz",
                "organizer_email": "juan@example.ph",
                "title": "Marikina Typhoon Relief 2026",
                "description": "Providing food and hygiene kits to flooded barangays.",
                "purpose": "Food packs and emergency supplies",
                "cause": "disaster_relief",
                "location": "Marikina City",
                "target_amount": 50000.0,
                "payment_method": "GCash",
                "payment_details": "0917-123-4567 (Juan D.)",
                "urgency": "high",
            }

            files = [
                ("documents", ("dswd_permit.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")),
            ]
            submit_resp = client.post(
                "/api/submissions",
                data={"campaign": json.dumps(campaign_payload)},
                files=files,
            )
            assert submit_resp.status_code == 201, f"Submit failed: {submit_resp.text}"
            sub_data = submit_resp.json()
            public_id = sub_data["public_id"]
            print(f"   [✓] Campaign created! Public ID: {public_id}")
            print(f"   Documents received: {sub_data['documents_received']}")

            # Retrieve the created document ID from database
            from backend.database import SessionLocal
            from backend import crud

            with SessionLocal() as db:
                camp = crud.get_campaign_by_public_id(db, public_id)
                assert camp is not None
                docs = crud.get_documents_by_campaign(db, camp.id)
                assert len(docs) == 1
                doc = docs[0]
                doc_id = doc.id
                print(f"   Document ID: {doc_id} (Status: {doc.processing_status})")

            # 3. Trigger document extraction
            print(f"\n3. Triggering Extraction on Document #{doc_id}...")
            extract_resp = client.post(f"/api/documents/{doc_id}/extract")
            assert extract_resp.status_code == 200, f"Extraction failed: {extract_resp.text}"
            ext_res = extract_resp.json()
            print(f"   Extraction Status: Success")
            print(f"   Confidence Notes: {ext_res.get('confidence_notes')}")

            # 4. Fetch full extraction result
            print(f"\n4. Fetching Full Extraction Details (/api/documents/{doc_id}/extraction)...")
            detail_resp = client.get(f"/api/documents/{doc_id}/extraction")
            assert detail_resp.status_code == 200
            details = detail_resp.json()

            print("\n--- Extracted Data Preview ---")
            print(f"Document Type:      {details.get('document_type')}")
            print(f"Issuing Authority:  {details.get('issuing_authority')}")
            print(f"Permit Number:      {details.get('permit_number')}")
            print(f"Organization Name:  {details.get('organization_name')}")
            print(f"Purpose:            {details.get('purpose')}")
            print(f"Issue Date:         {details.get('issue_date')}")
            print(f"Expiration Date:    {details.get('expiration_date')}")
            print(f"Beneficiaries:      {details.get('beneficiaries')}")
            print(f"Missing Fields:     {details.get('missing_fields')}")
            print(f"Raw Extracted Text: \n{details.get('raw_ocr_text')}")
            print("------------------------------")

            # 5. Check document endpoint
            doc_resp = client.get(f"/api/documents/{doc_id}")
            assert doc_resp.status_code == 200
            assert doc_resp.json()["processing_status"] == "completed"
            print("\n[✓] All tests passed! Pipeline verified end-to-end.")


if __name__ == "__main__":
    main_test()
