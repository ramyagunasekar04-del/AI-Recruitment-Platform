from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    User,
    CandidateProfile,
    EmployerProfile,
    Job,
    Application,
    MatchResult,
)

from app.core.dependencies import (
    get_current_user,
    require_role,
)

from app.modules.matching.service import (
    evaluate_application,
)


router = APIRouter(
    prefix="/matching",
    tags=["Matching"]
)


# ============================================================
# APPLY TO JOB
# ============================================================

@router.post("/apply/{job_id}")
@router.post("/jobs/{job_id}/apply")
def apply_to_job(
    job_id: int,
    current_user: User = Depends(
        require_role("candidate")
    ),
    db: Session = Depends(get_db),
):
    candidate = (
        db.query(CandidateProfile)
        .filter(
            CandidateProfile.user_id
            == current_user.id
        )
        .first()
    )

    if not candidate:
        raise HTTPException(
            status_code=404,
            detail="Candidate profile not found"
        )

    if not candidate.profile_json:
        raise HTTPException(
            status_code=400,
            detail="Complete candidate onboarding first."
        )

    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    if job.status != "PUBLISHED":
        raise HTTPException(
            status_code=400,
            detail="Only published jobs accept applications."
        )

    existing = (
        db.query(Application)
        .filter(
            Application.candidate_id == candidate.id,
            Application.job_id == job.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="You have already applied to this job."
        )

    application = Application(
        candidate_id=candidate.id,
        job_id=job.id,
        job_version=job.version,
        status="PENDING",
    )

    db.add(application)
    db.flush()

    result = evaluate_application(
        candidate,
        job
    )

    application.status = result["status"]

    match_result = MatchResult(
        application_id=application.id,
        status=result["status"],
        score=result["score"],
        criteria_json=result["criteria"],
        missing_criteria_json=result[
            "missing_criteria"
        ],
    )

    db.add(match_result)

    db.commit()
    db.refresh(application)

    return {
        "message": "Application submitted successfully.",
        "application_id": application.id,
        "job_id": job.id,
        "job_version": job.version,
        "status": result["status"],
        "score": result["score"],
        "mandatory_score": result[
            "mandatory_score"
        ],
        "optional_score": result[
            "optional_score"
        ],
        "criteria": result["criteria"],
        "missing_criteria": result[
            "missing_criteria"
        ],
        "unknown_criteria": result[
            "unknown_criteria"
        ],
    }


# ============================================================
# RE-RUN MATCHING
# ============================================================

@router.post(
    "/applications/{application_id}/match"
)
def match_application(
    application_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    application = (
        db.query(Application)
        .filter(
            Application.id == application_id
        )
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    candidate = application.candidate
    job = application.job

    is_candidate_owner = (
        current_user.role == "candidate"
        and candidate.user_id
        == current_user.id
    )

    employer_profile = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    is_employer_owner = (
        current_user.role == "employer"
        and employer_profile is not None
        and job.employer_id
        == employer_profile.id
    )

    if not (
        is_candidate_owner
        or is_employer_owner
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot access this application."
        )

    if application.job_version != job.version:
        raise HTTPException(
            status_code=409,
            detail="Application uses an older job version."
        )

    result = evaluate_application(
        candidate,
        job
    )

    application.status = result["status"]

    match_result = (
        db.query(MatchResult)
        .filter(
            MatchResult.application_id
            == application.id
        )
        .first()
    )

    if not match_result:
        match_result = MatchResult(
            application_id=application.id
        )
        db.add(match_result)

    match_result.status = result["status"]
    match_result.score = result["score"]
    match_result.criteria_json = result["criteria"]
    match_result.missing_criteria_json = result[
        "missing_criteria"
    ]

    db.commit()

    return {
        "application_id": application.id,
        "status": result["status"],
        "score": result["score"],
        "mandatory_score": result[
            "mandatory_score"
        ],
        "optional_score": result[
            "optional_score"
        ],
        "criteria": result["criteria"],
        "missing_criteria": result[
            "missing_criteria"
        ],
        "unknown_criteria": result[
            "unknown_criteria"
        ],
    }


# ============================================================
# GET MATCH RESULT
# ============================================================

@router.get(
    "/applications/{application_id}/match-result"
)
def get_match_result(
    application_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    application = (
        db.query(Application)
        .filter(
            Application.id == application_id
        )
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    candidate = application.candidate
    job = application.job

    is_candidate_owner = (
        current_user.role == "candidate"
        and candidate.user_id
        == current_user.id
    )

    employer_profile = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    is_employer_owner = (
        current_user.role == "employer"
        and employer_profile is not None
        and job.employer_id
        == employer_profile.id
    )

    if not (
        is_candidate_owner
        or is_employer_owner
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot access this match result."
        )

    result = application.match_result

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Match result not found"
        )

    criteria = result.criteria_json or []

    unknown_criteria = [
        item["criterion"]
        for item in criteria
        if item.get("status") == "UNKNOWN"
    ]

    return {
        "application_id": application.id,
        "job_id": job.id,
        "job_version": application.job_version,
        "status": result.status,
        "score": result.score,
        "criteria": criteria,
        "missing_criteria":
            result.missing_criteria_json or [],
        "unknown_criteria":
            unknown_criteria,
    }