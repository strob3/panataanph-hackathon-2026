"""Deterministic evidence-completeness scoring for submitted campaigns."""

from backend.schemas import CampaignCreate


def score_campaign(
    campaign: CampaignCreate,
    document_count: int,
    has_verified_history: bool,
) -> tuple[int, list[dict[str, str | int]]]:
    """Return a 0–100 evidence completeness score and its explainable findings.

    These checks measure information supplied with a submission. They do not
    establish document authenticity, campaign legitimacy, or proper use of funds.
    A human reviewer still makes the final approval decision.
    """
    findings: list[dict[str, str | int]] = []

    def add(criterion: str, awarded: int, possible: int, details: str) -> None:
        findings.append(
            {
                "criterion": criterion,
                "points_awarded": awarded,
                "points_possible": possible,
                "details": details,
            }
        )

    document_points = 30 if document_count else 0
    add(
        "supporting_documents",
        document_points,
        30,
        "At least one supporting document was submitted."
        if document_points
        else "No supporting documents were submitted.",
    )

    contact_points = 10 if campaign.organizer_email or campaign.organizer_phone else 0
    organization_points = (
        10
        if campaign.organization_name and campaign.organization_registration_number
        else 0
    )
    add(
        "organizer_information",
        contact_points + organization_points,
        20,
        "Organizer contact information and registered organization details are provided."
        if contact_points + organization_points == 20
        else "Some organizer contact or organization registration information is missing.",
    )

    payment_points = (10 if campaign.payment_method else 0) + (10 if campaign.payment_details else 0)
    add(
        "payment_information",
        payment_points,
        20,
        "Payment method and donation details are provided. Their ownership still needs human review."
        if payment_points == 20
        else "Provide the payment method and/or donation details to complete this section.",
    )

    complete_core_fields = all(
        [campaign.title, campaign.description, campaign.purpose, campaign.location]
    )
    completeness_points = (10 if complete_core_fields else 0)
    if campaign.beneficiaries:
        completeness_points += 5
    if len(campaign.description.strip()) >= 100:
        completeness_points += 5
    add(
        "campaign_completeness",
        completeness_points,
        20,
        "Core campaign information, beneficiaries, and a detailed description are present."
        if completeness_points == 20
        else "Add beneficiary information and a detailed description to complete this section.",
    )

    history_points = 10 if has_verified_history else 0
    add(
        "review_history",
        history_points,
        10,
        "This organizer has a previously verified campaign."
        if history_points
        else "No previously verified campaign is linked to this organizer account.",
    )

    return sum(int(item["points_awarded"]) for item in findings), findings
