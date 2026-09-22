import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.prompts import RESUME_PROFILE_PROMPT
from app.ai.schemas import CandidateProfileAI
from app.ai.wrapper import llm
from app.core.dependencies import get_current_user, require_role
from app.db.models import CandidateProfile, User
from app.db.session import get_db
from app.services.file_parser import extract_text_from_file


router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


UPLOAD_FOLDER = "uploads"
MAX_FILE_SIZE = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def validate_file(file: UploadFile):
    allowed_extensions = {".pdf", ".docx"}

    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and DOCX files are supported.",
        )

    return extension


@router.post("/candidate")
@router.post("/candidate/onboarding/resume")
async def upload_candidate_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    extension = validate_file(file)

    file_content = await file.read()

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File size must not exceed 5 MB.",
        )

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    server_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(UPLOAD_FOLDER, server_filename)

    with open(file_path, "wb") as output_file:
        output_file.write(file_content)

    try:
        resume_text = extract_text_from_file(file_path)
    except Exception as exc:
        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to read the uploaded document: {exc}",
        )

    if not resume_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded document does not contain readable text.",
        )

    prompt = RESUME_PROFILE_PROMPT.format(
        resume_text=resume_text[:20000]
    )

    try:
        profile_ai = llm.generate_structured(
            prompt,
            response_schema=CandidateProfileAI,
            temperature=0.1,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI profile extraction failed: {exc}",
        )

    profile_data = profile_ai.model_dump()

    profile_data["_confirmed"] = False

    candidate_profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == current_user.id)
        .first()
    )

    if candidate_profile:
        candidate_profile.resume_filename = server_filename
        candidate_profile.resume_path = file_path
        candidate_profile.resume_text = resume_text
        candidate_profile.profile_json = profile_data
    else:
        candidate_profile = CandidateProfile(
            user_id=current_user.id,
            resume_filename=server_filename,
            resume_path=file_path,
            resume_text=resume_text,
            profile_json=profile_data,
        )

        db.add(candidate_profile)

    db.commit()
    db.refresh(candidate_profile)

    return {
        "message": "Resume uploaded and profile extracted successfully.",
        "profile_confirmed": False,
        "profile": profile_data,
    }


@router.get("/candidate/profile")
async def get_candidate_profile(
    current_user: User = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )

    return {
        "id": profile.id,
        "profile": profile.profile_json or {},
        "resume_filename": profile.resume_filename,
        "confirmed": bool(
            (profile.profile_json or {}).get("_confirmed", False)
        ),
    }


@router.patch("/candidate/profile")
async def update_candidate_profile(
    updates: dict,
    current_user: User = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )

    current_profile = profile.profile_json or {}

    allowed_fields = {
        "summary",
        "skills",
        "education",
        "experience",
        "projects",
    }

    for field, value in updates.items():
        if field in allowed_fields:
            current_profile[field] = value

    current_profile["_confirmed"] = False

    profile.profile_json = current_profile

    db.commit()
    db.refresh(profile)

    return {
        "message": "Candidate profile updated. Please confirm it again.",
        "confirmed": False,
        "profile": profile.profile_json,
    }


@router.post("/candidate/profile/confirm")
async def confirm_candidate_profile(
    current_user: User = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )

    profile_data = profile.profile_json or {}

    profile_data["_confirmed"] = True

    profile.profile_json = profile_data

    db.commit()
    db.refresh(profile)

    return {
        "message": "Candidate profile confirmed successfully.",
        "confirmed": True,
        "profile": profile.profile_json,
    }


@router.post("/employer")
async def create_employer_profile(
    company_name: str,
    current_user: User = Depends(require_role("employer")),
    db: Session = Depends(get_db),
):
    from app.db.models import EmployerProfile

    existing_profile = (
        db.query(EmployerProfile)
        .filter(EmployerProfile.user_id == current_user.id)
        .first()
    )

    if existing_profile:
        existing_profile.company_name = company_name
    else:
        existing_profile = EmployerProfile(
            user_id=current_user.id,
            company_name=company_name,
        )
        db.add(existing_profile)

    db.commit()
    db.refresh(existing_profile)

    return {
        "message": "Employer profile created successfully.",
        "profile": {
            "id": existing_profile.id,
            "company_name": existing_profile.company_name,
        },
    }