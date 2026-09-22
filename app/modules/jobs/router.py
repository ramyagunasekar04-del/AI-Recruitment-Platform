from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.db.models import (
    User,
    EmployerProfile,
    Job,
    JobCriterion,
    SyllabusItem,
    Question,
)

from app.core.dependencies import require_role

from app.ai.wrapper import llm

from app.ai.schemas import (
    JobBlueprintAI,
    SyllabusAI,
    JobDescriptionAI,
    QuestionBankAI,
)

from app.modules.jobs.schemas import (
    JobCreateRequest,
)


router = APIRouter(
    prefix="/jobs",
    tags=["Job Intelligence"]
)


# ============================================================
# CREATE JOB
# ============================================================

@router.post("/")
def create_job(
    request: JobCreateRequest,
    current_user: User = Depends(
        require_role("employer")
    ),
    db: Session = Depends(get_db),
):
    employer = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    if not employer:
        raise HTTPException(
            status_code=400,
            detail="Complete employer onboarding first."
        )

    prompt = f"""
You are creating a structured job blueprint.

Extract only requirements explicitly stated
in the employer's job description.

Do not invent requirements.

Return:
role
mandatory_criteria
optional_criteria
skills
experience_requirements
education_requirements

Employer job description:

{request.description}
"""

    try:
        blueprint = llm.generate_structured(
            prompt,
            JobBlueprintAI,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI job blueprint failed: {str(exc)}"
        )

    blueprint_data = blueprint.model_dump()

    job = Job(
        employer_id=employer.id,
        title=request.title,
        description=request.description,
        status="DRAFT",
        version=1,
        blueprint_json=blueprint_data,
    )

    db.add(job)
    db.flush()

    for criterion in blueprint_data.get(
        "mandatory_criteria",
        []
    ):
        db.add(
            JobCriterion(
                job_id=job.id,
                criterion_text=criterion,
                criterion_type="mandatory",
                weight=1,
            )
        )

    for criterion in blueprint_data.get(
        "optional_criteria",
        []
    ):
        db.add(
            JobCriterion(
                job_id=job.id,
                criterion_text=criterion,
                criterion_type="optional",
                weight=1,
            )
        )

    db.commit()
    db.refresh(job)

    return {
        "message": "Job created successfully.",
        "job_id": job.id,
        "status": job.status,
        "version": job.version,
        "blueprint": job.blueprint_json,
    }


# ============================================================
# GET JOB
# ============================================================

@router.get("/{job_id}")
def get_job(
    job_id: int,
    current_user: User = Depends(
        require_role("candidate")
    ),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    if job.status != "PUBLISHED":
        raise HTTPException(
            status_code=404,
            detail="Job is not published."
        )

    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "status": job.status,
        "version": job.version,
        "blueprint": job.blueprint_json,
        "final_jd": job.final_jd,
    }


# ============================================================
# CONFIRM BLUEPRINT
# ============================================================

@router.post("/{job_id}/confirm")
def confirm_job(
    job_id: int,
    current_user: User = Depends(
        require_role("employer")
    ),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    employer = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    if not employer or job.employer_id != employer.id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this job."
        )

    if job.status != "DRAFT":
        raise HTTPException(
            status_code=409,
            detail="Only draft jobs can be confirmed."
        )

    job.status = "CONFIRMED"

    db.commit()

    return {
        "message": "Job blueprint confirmed.",
        "job_id": job.id,
        "status": job.status,
    }


# ============================================================
# GENERATE SYLLABUS
# ============================================================

@router.post("/{job_id}/generate-syllabus")
def generate_syllabus(
    job_id: int,
    current_user: User = Depends(
        require_role("employer")
    ),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    employer = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    if not employer or job.employer_id != employer.id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this job."
        )

    if job.status != "CONFIRMED":
        raise HTTPException(
            status_code=409,
            detail="Confirm the job blueprint first."
        )

    prompt = f"""
Create a structured interview syllabus.

Use only information supported by:

Job title:
{job.title}

Job description:
{job.description}

Confirmed job blueprint:
{job.blueprint_json}

Return a list of competency/topic/weight items.

Do not invent unrelated competencies.
"""

    try:
        syllabus = llm.generate_structured(
            prompt,
            SyllabusAI,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Syllabus generation failed: {str(exc)}"
        )

    # Remove previous syllabus if regenerated.
    db.query(SyllabusItem).filter(
        SyllabusItem.job_id == job.id
    ).delete()

    items = syllabus.model_dump()["items"]

    stored_items = []

    for index, item in enumerate(
        items,
        start=1
    ):
        syllabus_item = SyllabusItem(
            job_id=job.id,
            competency=item["competency"],
            topic=item["topic"],
            weight=item.get("weight", 1),
            display_order=index,
        )

        db.add(syllabus_item)

        stored_items.append({
            "competency": item["competency"],
            "topic": item["topic"],
            "weight": item.get("weight", 1),
            "display_order": index,
        })

    job.syllabus_json = {
        "items": stored_items
    }

    db.commit()

    return {
        "message": "Interview syllabus generated.",
        "job_id": job.id,
        "syllabus": stored_items,
    }


# ============================================================
# GET SYLLABUS
# ============================================================

@router.get("/{job_id}/syllabus")
def get_syllabus(
    job_id: int,
    current_user: User = Depends(
        require_role("employer")
    ),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    employer = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    if not employer or job.employer_id != employer.id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this job."
        )

    return {
        "job_id": job.id,
        "syllabus": job.syllabus_json
    }


# ============================================================
# GENERATE FINAL JD
# ============================================================

@router.post("/{job_id}/generate-jd")
def generate_final_jd(
    job_id: int,
    current_user: User = Depends(
        require_role("employer")
    ),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    employer = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    if not employer or job.employer_id != employer.id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this job."
        )

    if job.status != "CONFIRMED":
        raise HTTPException(
            status_code=409,
            detail="Job must be confirmed first."
        )

    if not job.syllabus_json:
        raise HTTPException(
            status_code=409,
            detail="Generate the syllabus first."
        )

    prompt = f"""
Create the final job description using ONLY
the confirmed job blueprint and interview syllabus.

Do not invent requirements.

Job title:
{job.title}

Confirmed blueprint:
{job.blueprint_json}

Interview syllabus:
{job.syllabus_json}

Return:
summary
responsibilities
must_have_criteria
good_to_have_criteria
experience
hiring_process
"""

    try:
        final_jd = llm.generate_structured(
            prompt,
            JobDescriptionAI,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Final JD generation failed: {str(exc)}"
        )

    job.final_jd = final_jd.model_dump()

    db.commit()

    return {
        "message": "Final job description generated.",
        "job_id": job.id,
        "final_jd": job.final_jd,
    }


# ============================================================
# GENERATE QUESTIONS
# ============================================================

@router.post("/{job_id}/generate-questions")
def generate_questions(
    job_id: int,
    current_user: User = Depends(
        require_role("employer")
    ),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    employer = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    if not employer or job.employer_id != employer.id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this job."
        )

    if job.status != "CONFIRMED":
        raise HTTPException(
            status_code=409,
            detail="Job must be confirmed first."
        )

    if not job.syllabus_json:
        raise HTTPException(
            status_code=409,
            detail="Generate the syllabus first."
        )

    prompt = f"""
Create a structured interview question bank.

Job title:
{job.title}

Job description:
{job.description}

Interview syllabus:
{job.syllabus_json}

Create questions that cover the syllabus.

Rules:
- Do not create unrelated questions.
- Every question must have a competency.
- Difficulty must be easy, medium, or hard.
- Questions should be appropriate for a professional interview.
"""

    try:
        question_bank = llm.generate_structured(
            prompt,
            QuestionBankAI,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Question generation failed: {str(exc)}"
        )

    db.query(Question).filter(
        Question.job_id == job.id
    ).delete()

    generated_questions = (
        question_bank.model_dump()["questions"]
    )

    stored_questions = []

    for item in generated_questions:

        syllabus_item = (
            db.query(SyllabusItem)
            .filter(
                SyllabusItem.job_id == job.id,
                SyllabusItem.competency
                == item["competency"],
            )
            .first()
        )

        question = Question(
            job_id=job.id,
            syllabus_item_id=(
                syllabus_item.id
                if syllabus_item
                else None
            ),
            question_text=item["question_text"],
            competency=item["competency"],
            difficulty=item.get(
                "difficulty",
                "medium"
            ),
            is_follow_up_allowed=True,
        )

        db.add(question)

        stored_questions.append({
            "question_text":
                item["question_text"],
            "competency":
                item["competency"],
            "difficulty":
                item.get(
                    "difficulty",
                    "medium"
                ),
        })

    db.commit()

    return {
        "message": "Interview question bank generated.",
        "job_id": job.id,
        "questions": stored_questions,
    }


# ============================================================
# GET QUESTIONS
# ============================================================

@router.get("/{job_id}/questions")
def get_questions(
    job_id: int,
    current_user: User = Depends(
        require_role("employer")
    ),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    employer = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    if not employer or job.employer_id != employer.id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this job."
        )

    questions = (
        db.query(Question)
        .filter(
            Question.job_id == job.id
        )
        .order_by(Question.id.asc())
        .all()
    )

    return {
        "job_id": job.id,
        "questions": [
            {
                "id": question.id,
                "question_text":
                    question.question_text,
                "competency":
                    question.competency,
                "difficulty":
                    question.difficulty,
                "is_follow_up_allowed":
                    question.is_follow_up_allowed,
            }
            for question in questions
        ],
    }


# ============================================================
# PUBLISH JOB
# ============================================================

@router.post("/{job_id}/publish")
def publish_job(
    job_id: int,
    current_user: User = Depends(
        require_role("employer")
    ),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    employer = (
        db.query(EmployerProfile)
        .filter(
            EmployerProfile.user_id
            == current_user.id
        )
        .first()
    )

    if not employer or job.employer_id != employer.id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this job."
        )

    if job.status != "CONFIRMED":
        raise HTTPException(
            status_code=409,
            detail="Only confirmed jobs can be published."
        )

    if not job.blueprint_json:
        raise HTTPException(
            status_code=409,
            detail="Job blueprint is missing."
        )

    if not job.criteria:
        raise HTTPException(
            status_code=409,
            detail="Job criteria are missing."
        )

    if not job.syllabus_json:
        raise HTTPException(
            status_code=409,
            detail="Interview syllabus is missing."
        )

    questions = (
        db.query(Question)
        .filter(
            Question.job_id == job.id
        )
        .count()
    )

    if questions == 0:
        raise HTTPException(
            status_code=409,
            detail="Interview questions are missing."
        )

    if not job.final_jd:
        raise HTTPException(
            status_code=409,
            detail="Final job description is missing."
        )

    job.status = "PUBLISHED"

    db.commit()

    return {
        "message": "Job published successfully.",
        "job_id": job.id,
        "status": job.status,
        "version": job.version,
    }


# ============================================================
# LIST PUBLISHED JOBS
# ============================================================

@router.get("/")
def list_jobs(
    current_user: User = Depends(
        require_role("candidate")
    ),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(Job)
        .filter(
            Job.status == "PUBLISHED"
        )
        .order_by(
            Job.created_at.desc()
        )
        .all()
    )

    return {
        "jobs": [
            {
                "id": job.id,
                "title": job.title,
                "description":
                    job.description,
                "version":
                    job.version,
                "final_jd":
                    job.final_jd,
            }
            for job in jobs
        ]
    }