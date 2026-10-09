"""
PanataanPH Seed Data Script.

Populates the database with realistic but fictional Philippine relief
campaign data for development and demonstration purposes.

⚠️  ALL DATA IN THIS FILE IS FICTIONAL.
    Organization names, people, permits, and details are entirely made up
    and do not represent real entities or campaigns.

Run from the src/ directory:
    python -m backend.seed
"""

import json

from backend.database import init_db, SessionLocal
from backend import crud
from backend.models import Campaign


def seed_database() -> None:
    """Insert sample campaigns, documents, extractions, reviews, reports, and findings."""

    db = SessionLocal()

    # Check if data already exists to prevent duplicates
    existing = db.query(Campaign).first()
    if existing is not None:
        print("⚠️  Database already contains data. Skipping seed.")
        print("💡 To re-seed, delete the database file and run again.")
        db.close()
        return

    try:
        # ================================================================
        # Campaign 1: Verified typhoon relief — Leyte
        # ================================================================
        print("📦 Creating Campaign 1: Typhoon Relief - Leyte...")
        c1 = crud.create_campaign(
            db,
            organizer_name="Maria Santos",
            organizer_email="maria.santos@example.com",
            organizer_phone="+63 917 123 4567",
            organization_name="Tulong Leyte Foundation",
            organization_registration_number="SEC-2024-00456",
            title="Typhoon Yolanda Recovery Fund for Eastern Leyte",
            description=(
                "This campaign aims to provide immediate relief and long-term recovery "
                "assistance to families affected by Typhoon Yolanda in Eastern Leyte. "
                "Funds will be used for food packs, temporary shelter materials, clean "
                "water supply, and livelihood restoration programs."
            ),
            purpose="Typhoon Relief",
            cause="disaster_relief",
            location="Tacloban City, Leyte",
            beneficiaries="500 families in Barangays 64, 65, and 66 of Tacloban City",
            target_amount=2500000.00,
            payment_method="Bank Transfer / GCash",
            payment_details="BDO Savings Account: 1234-5678-9012 (Tulong Leyte Foundation) | GCash: 0917-123-4567",
            urgency="high",
            status="verified",
            verification_score=85,
            score_breakdown=json.dumps({
                "permits": 25,
                "identity": 20,
                "consistency": 18,
                "completeness": 16,
                "history": 6,
            }),
        )

        # Documents for Campaign 1
        d1_1 = crud.create_document(
            db,
            campaign_id=c1.id,
            storage_path="storage/documents/c1_solicitation_permit.pdf",
            original_filename="DSWD_Solicitation_Permit_2026.pdf",
            file_type="pdf",
            file_size_bytes=245760,
        )
        crud.update_document_status(db, d1_1.id, "completed")

        d1_2 = crud.create_document(
            db,
            campaign_id=c1.id,
            storage_path="storage/documents/c1_sec_registration.pdf",
            original_filename="SEC_Registration_Certificate.pdf",
            file_type="pdf",
            file_size_bytes=189440,
        )
        crud.update_document_status(db, d1_2.id, "completed")

        # Extraction results for Campaign 1 documents
        crud.create_extraction_result(
            db,
            document_id=d1_1.id,
            document_type="Solicitation Permit",
            issuing_authority="Department of Social Welfare and Development (DSWD)",
            permit_number="DSWD-SP-2026-00789",
            organization_name="Tulong Leyte Foundation, Inc.",
            purpose="Typhoon Yolanda Recovery and Relief Operations",
            issue_date="2026-08-15",
            expiration_date="2026-12-31",
            beneficiaries=None,
            missing_fields=json.dumps(["beneficiaries"]),
            raw_ocr_text="[Sample OCR text for demonstration]",
            raw_llm_response=json.dumps({
                "document_type": "Solicitation Permit",
                "issuing_authority": "Department of Social Welfare and Development (DSWD)",
                "permit_number": "DSWD-SP-2026-00789",
                "organization_name": "Tulong Leyte Foundation, Inc.",
                "purpose": "Typhoon Yolanda Recovery and Relief Operations",
                "issue_date": "2026-08-15",
                "expiration_date": "2026-12-31",
                "beneficiaries": None,
                "missing_fields": ["beneficiaries"],
            }),
            confidence_notes="High confidence. Clear scan with selectable text.",
        )

        crud.create_extraction_result(
            db,
            document_id=d1_2.id,
            document_type="SEC Registration Certificate",
            issuing_authority="Securities and Exchange Commission (SEC)",
            permit_number="CN-2024-00456",
            organization_name="Tulong Leyte Foundation, Inc.",
            purpose="Non-stock, non-profit corporation for disaster relief",
            issue_date="2024-03-10",
            expiration_date=None,
            beneficiaries=None,
            missing_fields=json.dumps(["expiration_date", "beneficiaries"]),
            raw_ocr_text="[Sample OCR text for demonstration]",
            raw_llm_response="{}",
            confidence_notes="Good quality scan.",
        )

        # Review for Campaign 1
        crud.create_review(
            db,
            campaign_id=c1.id,
            admin_username="admin_garcia",
            decision="approved",
            reason="All documents verified. DSWD permit is valid. SEC registration confirmed. Organization name matches across all documents.",
            previous_status="under_review",
            new_status="verified",
        )

        # Findings for Campaign 1
        crud.create_finding(db, c1.id, "permits", 25, 30, "DSWD solicitation permit provided and valid. Minor: beneficiaries not explicitly listed in the permit.")
        crud.create_finding(db, c1.id, "identity", 20, 20, "SEC registration provided. Organization name and registration number verified.")
        crud.create_finding(db, c1.id, "consistency", 18, 20, "Organization name consistent across documents. Bank account name matches. Minor discrepancy: GCash registered to individual, not org.")
        crud.create_finding(db, c1.id, "completeness", 16, 20, "Campaign details are thorough. Missing: detailed budget breakdown and timeline.")
        crud.create_finding(db, c1.id, "history", 6, 10, "First campaign on the platform. No prior review history.")

        # ================================================================
        # Campaign 2: Pending flood relief — Cagayan
        # ================================================================
        print("📦 Creating Campaign 2: Flood Relief - Cagayan...")
        c2 = crud.create_campaign(
            db,
            organizer_name="Juan dela Cruz",
            organizer_email="juan.delacruz@example.com",
            organizer_phone="+63 928 987 6543",
            organization_name="Cagayan Flood Response Network",
            title="Emergency Flood Relief for Cagayan Valley Families",
            description=(
                "Urgent assistance needed for families displaced by severe flooding in "
                "Cagayan Valley. The campaign will provide emergency food supplies, "
                "hygiene kits, blankets, and evacuation support for affected communities "
                "along the Cagayan River."
            ),
            purpose="Flood Relief",
            cause="disaster_relief",
            location="Tuguegarao City, Cagayan",
            beneficiaries="Displaced families in flood-affected barangays along the Cagayan River",
            target_amount=1800000.00,
            payment_method="GCash",
            payment_details="GCash: 0928-987-6543 (Juan dela Cruz)",
            urgency="critical",
            status="pending",
        )

        # Document for Campaign 2
        d2_1 = crud.create_document(
            db,
            campaign_id=c2.id,
            storage_path="storage/documents/c2_barangay_endorsement.pdf",
            original_filename="Barangay_Endorsement_Letter.pdf",
            file_type="pdf",
            file_size_bytes=132096,
        )

        # ================================================================
        # Campaign 3: Under review medical — Manila
        # ================================================================
        print("📦 Creating Campaign 3: Medical Assistance - Manila...")
        c3 = crud.create_campaign(
            db,
            organizer_name="Dr. Ana Reyes",
            organizer_email="ana.reyes@example.com",
            organizer_phone="+63 906 555 1234",
            organization_name="Kalusugan Para sa Lahat",
            organization_registration_number="SEC-2025-01234",
            title="Free Medical Mission for Urban Poor Communities in Manila",
            description=(
                "A comprehensive medical mission providing free check-ups, laboratory "
                "tests, dental services, and essential medicines to underserved "
                "communities in Tondo, Manila. The campaign also aims to conduct health "
                "education seminars on disease prevention and nutrition."
            ),
            purpose="Medical Assistance",
            cause="medical",
            location="Tondo, Manila",
            beneficiaries="Residents of Barangays 105, 106, and 107 in Tondo, Manila",
            target_amount=750000.00,
            payment_method="Bank Transfer",
            payment_details="BPI Checking Account: 9876-5432-1098 (Kalusugan Para sa Lahat)",
            urgency="normal",
            status="under_review",
            verification_score=62,
            score_breakdown=json.dumps({
                "permits": 18,
                "identity": 15,
                "consistency": 12,
                "completeness": 14,
                "history": 3,
            }),
        )

        # Documents for Campaign 3
        d3_1 = crud.create_document(
            db,
            campaign_id=c3.id,
            storage_path="storage/documents/c3_doh_permit.pdf",
            original_filename="DOH_Health_Event_Permit.pdf",
            file_type="pdf",
            file_size_bytes=198656,
        )
        crud.update_document_status(db, d3_1.id, "completed")

        crud.create_extraction_result(
            db,
            document_id=d3_1.id,
            document_type="Health Event Permit",
            issuing_authority="Department of Health (DOH) - NCR",
            permit_number="DOH-NCR-HEP-2026-0456",
            organization_name="Kalusugan Para sa Lahat Inc.",
            purpose="Free Medical Mission and Health Education",
            issue_date="2026-09-01",
            expiration_date="2026-11-30",
            beneficiaries="Urban poor communities in Tondo, Manila",
            missing_fields=json.dumps([]),
            raw_ocr_text="[Sample OCR text for demonstration]",
            raw_llm_response="{}",
            confidence_notes="Moderate confidence. Some text slightly blurred but readable.",
        )

        # Review for Campaign 3 (moved to under_review)
        crud.create_review(
            db,
            campaign_id=c3.id,
            admin_username="admin_garcia",
            decision="under_review",
            reason="Documents received. Reviewing permit validity and organization registration.",
            previous_status="pending",
            new_status="under_review",
        )

        # Findings for Campaign 3
        crud.create_finding(db, c3.id, "permits", 18, 30, "DOH health event permit provided. DSWD solicitation permit not yet submitted for fundraising aspect.")
        crud.create_finding(db, c3.id, "identity", 15, 20, "SEC registration number provided but certificate not uploaded for verification.")
        crud.create_finding(db, c3.id, "consistency", 12, 20, "Organization name slight variation between permit ('Inc.') and submission. Bank account name pending verification.")
        crud.create_finding(db, c3.id, "completeness", 14, 20, "Core details provided. Missing: detailed budget, volunteer list, partner hospital/clinic information.")
        crud.create_finding(db, c3.id, "history", 3, 10, "No previous campaigns. Organization is new to the platform.")

        # ================================================================
        # Campaign 4: Rejected campaign
        # ================================================================
        print("📦 Creating Campaign 4: Rejected Campaign...")
        c4 = crud.create_campaign(
            db,
            organizer_name="Roberto Villanueva",
            organizer_email="r.villanueva@example.com",
            organization_name="Quick Help PH",
            title="Earthquake Victims Emergency Fund - Batangas",
            description=(
                "Emergency fundraiser for earthquake victims in Batangas province. "
                "Funds will be used for rescue operations and rebuilding efforts."
            ),
            purpose="Earthquake Relief",
            cause="disaster_relief",
            location="Batangas City, Batangas",
            target_amount=5000000.00,
            payment_method="GCash",
            payment_details="GCash: 0999-000-0000",
            urgency="critical",
            status="rejected",
            verification_score=18,
            score_breakdown=json.dumps({
                "permits": 0,
                "identity": 5,
                "consistency": 3,
                "completeness": 8,
                "history": 2,
            }),
        )

        # Document for Campaign 4
        d4_1 = crud.create_document(
            db,
            campaign_id=c4.id,
            storage_path="storage/documents/c4_blurry_document.jpg",
            original_filename="support_document.jpg",
            file_type="jpg",
            file_size_bytes=87040,
        )
        crud.update_document_status(db, d4_1.id, "completed")

        crud.create_extraction_result(
            db,
            document_id=d4_1.id,
            document_type=None,
            issuing_authority=None,
            permit_number=None,
            organization_name=None,
            purpose=None,
            issue_date=None,
            expiration_date=None,
            beneficiaries=None,
            missing_fields=json.dumps([
                "document_type", "issuing_authority", "permit_number",
                "organization_name", "purpose", "issue_date",
                "expiration_date", "beneficiaries"
            ]),
            raw_ocr_text="[Largely unreadable - poor image quality]",
            raw_llm_response="{}",
            confidence_notes="Very low confidence. Image is blurry and most text is unreadable.",
        )

        # Reviews for Campaign 4
        crud.create_review(
            db,
            campaign_id=c4.id,
            admin_username="admin_santos",
            decision="needs_information",
            reason="Uploaded document is unreadable. Please provide a clearer scan of your permit or authorization.",
            previous_status="pending",
            new_status="needs_information",
        )
        # Re-fetch so that the status is correct before the next review
        c4 = crud.get_campaign_by_id(db, c4.id)
        crud.create_review(
            db,
            campaign_id=c4.id,
            admin_username="admin_santos",
            decision="rejected",
            reason="No additional documents provided within the requested timeframe. "
                   "Organization registration could not be verified. "
                   "Campaign may be resubmitted with proper documentation.",
            previous_status="needs_information",
            new_status="rejected",
        )

        # Findings for Campaign 4
        crud.create_finding(db, c4.id, "permits", 0, 30, "No valid permit or authorization document provided. Uploaded image was unreadable.")
        crud.create_finding(db, c4.id, "identity", 5, 20, "Organizer name provided but no supporting ID or SEC registration.")
        crud.create_finding(db, c4.id, "consistency", 3, 20, "Cannot verify consistency — insufficient documentation. GCash registered to unknown number.")
        crud.create_finding(db, c4.id, "completeness", 8, 20, "Basic campaign info provided but lacks detail. No budget, timeline, or beneficiary specifics.")
        crud.create_finding(db, c4.id, "history", 2, 10, "No previous campaigns. Unable to establish credibility.")

        # ================================================================
        # Campaign 5: Needs information — Education — Mindanao
        # ================================================================
        print("📦 Creating Campaign 5: Education Campaign - Mindanao...")
        c5 = crud.create_campaign(
            db,
            organizer_name="Fatima Abdulrahman",
            organizer_email="fatima.a@example.com",
            organizer_phone="+63 935 444 7890",
            organization_name="Aral Mindanao Inc.",
            organization_registration_number="SEC-2025-07890",
            title="School Rebuilding Project for Conflict-Affected Areas in Lanao del Sur",
            description=(
                "This project aims to rebuild and repair three elementary schools in "
                "Lanao del Sur that were damaged during the Marawi crisis. The fund will "
                "cover construction materials, classroom furniture, learning supplies, "
                "and teacher training programs to help children return to quality education."
            ),
            purpose="Education",
            cause="education",
            location="Marawi City, Lanao del Sur",
            beneficiaries="Approximately 800 elementary school children in three barangays",
            target_amount=3200000.00,
            payment_method="Bank Transfer / GCash",
            payment_details="Landbank Savings: 3456-7890-1234 (Aral Mindanao Inc.) | GCash: 0935-444-7890",
            urgency="normal",
            status="needs_information",
            verification_score=45,
            score_breakdown=json.dumps({
                "permits": 10,
                "identity": 12,
                "consistency": 10,
                "completeness": 10,
                "history": 3,
            }),
        )

        # Document for Campaign 5
        d5_1 = crud.create_document(
            db,
            campaign_id=c5.id,
            storage_path="storage/documents/c5_deped_endorsement.pdf",
            original_filename="DepEd_Endorsement_Letter.pdf",
            file_type="pdf",
            file_size_bytes=176128,
        )
        crud.update_document_status(db, d5_1.id, "completed")

        crud.create_extraction_result(
            db,
            document_id=d5_1.id,
            document_type="Endorsement Letter",
            issuing_authority="Department of Education (DepEd) - Region X",
            permit_number=None,
            organization_name="Aral Mindanao Inc.",
            purpose="School Rebuilding and Repair Project",
            issue_date="2026-07-20",
            expiration_date=None,
            beneficiaries="Elementary school children in Marawi City",
            missing_fields=json.dumps(["permit_number", "expiration_date"]),
            raw_ocr_text="[Sample OCR text for demonstration]",
            raw_llm_response="{}",
            confidence_notes="Good quality. Endorsement letter, not a permit — no permit number expected.",
        )

        # Review for Campaign 5
        crud.create_review(
            db,
            campaign_id=c5.id,
            admin_username="admin_garcia",
            decision="needs_information",
            reason="DepEd endorsement received, but DSWD solicitation permit or LGU authorization is required for public fundraising. Please upload the applicable permit.",
            previous_status="pending",
            new_status="needs_information",
        )

        # Findings for Campaign 5
        crud.create_finding(db, c5.id, "permits", 10, 30, "DepEd endorsement provided but solicitation permit or LGU authorization still required.")
        crud.create_finding(db, c5.id, "identity", 12, 20, "SEC number provided. Certificate upload needed for full verification.")
        crud.create_finding(db, c5.id, "consistency", 10, 20, "Organization name matches on endorsement letter. Bank account verification pending.")
        crud.create_finding(db, c5.id, "completeness", 10, 20, "Good description but missing detailed budget and construction timeline.")
        crud.create_finding(db, c5.id, "history", 3, 10, "First campaign on the platform.")

        # ================================================================
        # Campaign 6: Verified earthquake relief — Cebu
        # ================================================================
        print("📦 Creating Campaign 6: Earthquake Relief - Cebu...")
        c6 = crud.create_campaign(
            db,
            organizer_name="Carlos Mendoza",
            organizer_email="carlos.mendoza@example.com",
            organizer_phone="+63 912 678 9012",
            organization_name="Bangon Sugbo Movement",
            organization_registration_number="SEC-2023-03456",
            title="Cebu Earthquake Emergency Response and Housing Assistance",
            description=(
                "Emergency response campaign for the recent earthquake in Cebu province. "
                "This campaign provides temporary housing, structural assessments for "
                "damaged homes, emergency food and water, medical assistance, and trauma "
                "counseling for affected families. Partner organizations include local "
                "government units and accredited volunteer groups."
            ),
            purpose="Earthquake Relief",
            cause="disaster_relief",
            location="Cebu City, Cebu",
            beneficiaries="300+ families in earthquake-affected areas of Cebu City and surrounding municipalities",
            target_amount=4000000.00,
            payment_method="Bank Transfer / GCash / Maya",
            payment_details="Metrobank Savings: 5678-9012-3456 (Bangon Sugbo Movement) | GCash: 0912-678-9012 | Maya: 0912-678-9012",
            urgency="critical",
            status="verified",
            verification_score=92,
            score_breakdown=json.dumps({
                "permits": 28,
                "identity": 20,
                "consistency": 20,
                "completeness": 18,
                "history": 6,
            }),
        )

        # Documents for Campaign 6
        d6_1 = crud.create_document(
            db,
            campaign_id=c6.id,
            storage_path="storage/documents/c6_dswd_permit.pdf",
            original_filename="DSWD_Solicitation_Permit_Cebu.pdf",
            file_type="pdf",
            file_size_bytes=267264,
        )
        crud.update_document_status(db, d6_1.id, "completed")

        d6_2 = crud.create_document(
            db,
            campaign_id=c6.id,
            storage_path="storage/documents/c6_sec_cert.pdf",
            original_filename="SEC_Certificate_Bangon_Sugbo.pdf",
            file_type="pdf",
            file_size_bytes=201728,
        )
        crud.update_document_status(db, d6_2.id, "completed")

        d6_3 = crud.create_document(
            db,
            campaign_id=c6.id,
            storage_path="storage/documents/c6_lgu_endorsement.pdf",
            original_filename="Cebu_City_LGU_Endorsement.pdf",
            file_type="pdf",
            file_size_bytes=143360,
        )
        crud.update_document_status(db, d6_3.id, "completed")

        # Extraction results for Campaign 6 documents
        crud.create_extraction_result(
            db,
            document_id=d6_1.id,
            document_type="Solicitation Permit",
            issuing_authority="Department of Social Welfare and Development (DSWD) - Region VII",
            permit_number="DSWD-VII-SP-2026-01234",
            organization_name="Bangon Sugbo Movement, Inc.",
            purpose="Earthquake Emergency Response and Housing Assistance",
            issue_date="2026-09-20",
            expiration_date="2027-03-20",
            beneficiaries="Earthquake-affected families in Cebu City and surrounding areas",
            missing_fields=json.dumps([]),
            raw_ocr_text="[Sample OCR text for demonstration]",
            raw_llm_response="{}",
            confidence_notes="High confidence. Clear document with selectable text.",
        )

        crud.create_extraction_result(
            db,
            document_id=d6_2.id,
            document_type="SEC Registration Certificate",
            issuing_authority="Securities and Exchange Commission (SEC)",
            permit_number="CN-2023-03456",
            organization_name="Bangon Sugbo Movement, Inc.",
            purpose="Non-stock, non-profit corporation for disaster response",
            issue_date="2023-06-15",
            expiration_date=None,
            beneficiaries=None,
            missing_fields=json.dumps(["expiration_date", "beneficiaries"]),
            raw_ocr_text="[Sample OCR text for demonstration]",
            raw_llm_response="{}",
            confidence_notes="Good quality document.",
        )

        crud.create_extraction_result(
            db,
            document_id=d6_3.id,
            document_type="LGU Endorsement Letter",
            issuing_authority="Office of the Mayor, Cebu City",
            permit_number=None,
            organization_name="Bangon Sugbo Movement",
            purpose="Endorsement for earthquake relief operations in Cebu City",
            issue_date="2026-09-22",
            expiration_date=None,
            beneficiaries="Residents of earthquake-affected barangays",
            missing_fields=json.dumps(["permit_number", "expiration_date"]),
            raw_ocr_text="[Sample OCR text for demonstration]",
            raw_llm_response="{}",
            confidence_notes="Endorsement letter — no permit number expected.",
        )

        # Review for Campaign 6
        crud.create_review(
            db,
            campaign_id=c6.id,
            admin_username="admin_santos",
            decision="approved",
            reason=(
                "Complete documentation provided. DSWD solicitation permit is valid through "
                "March 2027. SEC registration confirmed. LGU endorsement from Cebu City "
                "verified. Organization name consistent across all documents. Payment "
                "accounts registered to the organization."
            ),
            previous_status="under_review",
            new_status="verified",
        )

        # Findings for Campaign 6
        crud.create_finding(db, c6.id, "permits", 28, 30, "DSWD solicitation permit valid. LGU endorsement provided. Minor: no barangay-level clearances submitted.")
        crud.create_finding(db, c6.id, "identity", 20, 20, "SEC registration certificate provided and verified. Organization established since 2023.")
        crud.create_finding(db, c6.id, "consistency", 20, 20, "Organization name consistent across all 3 documents. Payment accounts registered to org name.")
        crud.create_finding(db, c6.id, "completeness", 18, 20, "Comprehensive campaign details. Minor: specific budget per activity not provided.")
        crud.create_finding(db, c6.id, "history", 6, 10, "First campaign but strong documentation. Organization has 3+ years of SEC registration.")

        # ================================================================
        # Sample Reports
        # ================================================================
        print("📦 Creating sample reports...")
        crud.create_report(
            db,
            campaign_id=c1.id,
            reason="I noticed the GCash number listed is different from the one posted on their official Facebook page. Can an admin please verify?",
            reporter_name="Concerned Donor",
            reporter_email="donor@example.com",
        )

        crud.create_report(
            db,
            campaign_id=c3.id,
            reason="I live in Tondo and I haven't heard about this medical mission from our barangay officials. Is this legitimate?",
            reporter_name=None,
            reporter_email=None,
        )

        print()
        print("=" * 60)
        print("✅ Seed data inserted successfully!")
        print("=" * 60)
        print()
        print("📊 Summary:")
        print(f"   • 6 campaigns (2 verified, 1 under_review, 1 pending, 1 needs_info, 1 rejected)")
        print(f"   • 9 documents with metadata")
        print(f"   • 7 extraction results")
        print(f"   • 5 admin reviews")
        print(f"   • 2 user reports")
        print(f"   • 25 verification findings")
        print()

    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")
        raise
    finally:
        db.close()


def main() -> None:
    print("🔧 Initializing database tables...")
    init_db()
    print()
    print("🌱 Seeding database with fictional data...")
    seed_database()


if __name__ == "__main__":
    main()
