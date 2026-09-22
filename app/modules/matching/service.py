import re

from app.db.models import (
    CandidateProfile,
    Job,
    JobCriterion,
)


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9+#.\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def extract_keywords(text: str) -> list[str]:
    normalized = normalize_text(text)

    words = normalized.split()

    stop_words = {
        "and",
        "or",
        "the",
        "a",
        "an",
        "with",
        "for",
        "to",
        "of",
        "in",
        "on",
        "is",
        "are",
        "years",
        "year",
        "experience",
        "knowledge",
        "required",
        "must",
        "have",
        "should",
    }

    return [
        word
        for word in words
        if word not in stop_words
        and len(word) > 2
    ]


def build_candidate_text(
    candidate: CandidateProfile
) -> str:

    profile = candidate.profile_json or {}

    parts = [
        candidate.resume_text or "",
        profile.get("summary", ""),
    ]

    for field in [
        "skills",
        "education",
        "experience",
        "projects",
    ]:
        value = profile.get(field, [])

        if isinstance(value, list):
            parts.extend(
                str(item)
                for item in value
            )

        elif value:
            parts.append(str(value))

    return normalize_text(
        " ".join(parts)
    )


def evaluate_criterion(
    candidate_text: str,
    criterion: JobCriterion,
) -> dict:

    criterion_text = criterion.criterion_text

    normalized_candidate = normalize_text(
        candidate_text
    )

    normalized_criterion = normalize_text(
        criterion_text
    )

    # Exact phrase match.
    if normalized_criterion in normalized_candidate:
        return {
            "status": "MET",
            "evidence": (
                f"Candidate profile/resume contains "
                f"the required criterion: "
                f"{criterion_text}"
            ),
        }

    keywords = extract_keywords(
        criterion_text
    )

    if not keywords:
        return {
            "status": "UNKNOWN",
            "evidence": (
                "Criterion could not be evaluated "
                "from available structured text."
            ),
        }

    matched = [
        word
        for word in keywords
        if word in normalized_candidate
    ]

    ratio = len(matched) / len(keywords)

    if ratio >= 0.70:
        return {
            "status": "MET",
            "evidence": (
                "Matched candidate evidence: "
                + ", ".join(matched)
            ),
        }

    if ratio > 0:
        return {
            "status": "UNKNOWN",
            "evidence": (
                "Partial evidence found: "
                + ", ".join(matched)
            ),
        }

    return {
        "status": "NOT_MET",
        "evidence": (
            "No matching evidence was found "
            "for this criterion."
        ),
    }


def evaluate_application(
    candidate: CandidateProfile,
    job: Job,
) -> dict:

    profile_data = candidate.profile_json or {}

    # Candidate must explicitly confirm
    # the AI-generated profile.
    if not profile_data.get(
        "_confirmed",
        False
    ):
        return {
            "status": "UNKNOWN",
            "score": 0.0,
            "mandatory_score": 0.0,
            "optional_score": 0.0,
            "criteria": [],
            "missing_criteria": [],
            "unknown_criteria": [
                "Candidate profile has not been confirmed"
            ],
            "job_version": job.version,
        }

    candidate_text = build_candidate_text(
        candidate
    )

    criteria = []

    mandatory_results = []
    optional_results = []

    for criterion in job.criteria:

        result = evaluate_criterion(
            candidate_text,
            criterion
        )

        item = {
            "criterion_id": criterion.id,
            "criterion": criterion.criterion_text,
            "criterion_type": criterion.criterion_type,
            "weight": criterion.weight,
            "status": result["status"],
            "evidence": result["evidence"],
        }

        criteria.append(item)

        if criterion.criterion_type == "mandatory":
            mandatory_results.append(item)
        else:
            optional_results.append(item)

    mandatory_total = len(
        mandatory_results
    )

    mandatory_met = sum(
        1
        for item in mandatory_results
        if item["status"] == "MET"
    )

    mandatory_score = (
        mandatory_met / mandatory_total * 100
        if mandatory_total
        else 100.0
    )

    missing_criteria = [
        item["criterion"]
        for item in mandatory_results
        if item["status"] == "NOT_MET"
    ]

    unknown_criteria = [
        item["criterion"]
        for item in mandatory_results
        if item["status"] == "UNKNOWN"
    ]

    # Hard gate.
    if missing_criteria:
        final_status = "NOT_ELIGIBLE"

    elif unknown_criteria:
        final_status = "UNKNOWN"

    else:
        final_status = "MATCHED"

    # Optional weighted score.
    optional_score = 0.0

    if optional_results:

        total_weight = sum(
            max(item["weight"], 1)
            for item in optional_results
        )

        earned_weight = sum(
            max(item["weight"], 1)
            for item in optional_results
            if item["status"] == "MET"
        )

        optional_score = (
            earned_weight / total_weight * 100
            if total_weight
            else 0.0
        )

    # Final deterministic score.
    if optional_results:
        final_score = (
            mandatory_score * 0.70
            + optional_score * 0.30
        )
    else:
        final_score = mandatory_score

    return {
        "status": final_status,
        "score": round(final_score, 2),
        "mandatory_score": round(
            mandatory_score,
            2
        ),
        "optional_score": round(
            optional_score,
            2
        ),
        "criteria": criteria,
        "missing_criteria": missing_criteria,
        "unknown_criteria": unknown_criteria,
        "job_version": job.version,
    }