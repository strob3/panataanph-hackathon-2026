"""Deterministic evidence completeness score from documented 30/20/20/20/10 weights."""

from backend.models import Campaign

# Eligibility for ordinary human approval; exceptions require a recorded review.
MIN_VERIFICATION_SCORE = 80


def score_campaign(campaign: Campaign, *, permits: bool, identity: bool, consistency: bool, history: bool) -> list[dict]:
    """Award confirmed criterion weights; never infer authenticity from file count.

    Permits require an admin's applicable-authorizations check and evidence.
    Identity requires a verified owner plus the admin identity check and evidence.
    Consistency requires the admin check and donation method/details.
    Completeness awards 4 points each for title+description, purpose, location,
    beneficiaries, and positive target amount. History requires the admin check.
    Missing evidence yields missing points, never a fraud allegation.
    """
    complete = [bool(campaign.title and campaign.description), bool(campaign.purpose), bool(campaign.location), bool(campaign.beneficiaries), campaign.target_amount > 0]
    evidence = bool(campaign.documents)
    criteria = [
        ("permits", 30 if permits and evidence else 0, 30, "Applicable permits/authorizations confirmed by reviewer with submitted evidence."),
        ("identity", 20 if identity and evidence and campaign.owner is not None and campaign.owner.verified else 0, 20, "Organizer account verified and identity evidence confirmed by reviewer."),
        ("consistency", 20 if consistency and campaign.payment_method and campaign.payment_details else 0, 20, "Organizer and donation details confirmed consistent by reviewer."),
        ("completeness", 4 * sum(complete), 20, "4 points each: title/description, purpose, location, beneficiaries, positive target."),
        ("history", 10 if history else 0, 10, "Previously reviewed campaign history checked by reviewer."),
    ]
    return [dict(criterion=name, points_awarded=points, points_possible=maximum, details=details) for name, points, maximum, details in criteria]
