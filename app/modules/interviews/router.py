from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.db.models import (
    User,
    Application,
    MatchResult,
    InterviewSession,
    InterviewAnswer,
    Question,
)

from app.core.dependencies import (
    require_role,
)

from app.ai.wrapper import llm


router = APIRouter(
    prefix="/interviews",
    tags=["Structured AI Interview"]
)


# ============================================================
# HELPER - CHECK APPLICATION OWNERSHIP
# ============================================================

def get_candidate_application(
    application_id: int,
    current_user: User,
    db: Session,
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
            detail="Application not found."
        )

    if application.candidate.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access this application."
        )

    return application


# ============================================================
# HELPER - GET QUESTIONS
# ============================================================

def get_job_questions(
    application: Application,
    db: Session,
):
    return (
        db.query(Question)
        .filter(
            Question.job_id
            == application.job_id
        )
        .order_by(Question.id.asc())
        .all()
    )


# ============================================================
# START INTERVIEW
# ============================================================

@router.post("/start/{application_id}")
def start_interview(
    application_id: int,
    current_user: User = Depends(
        require_role("candidate")
    ),
    db: Session = Depends(get_db),
):
    application = get_candidate_application(
        application_id,
        current_user,
        db,
    )

    match_result = (
        db.query(MatchResult)
        .filter(
            MatchResult.application_id
            == application.id
        )
        .first()
    )

    if not match_result:
        raise HTTPException(
            status_code=409,
            detail="Matching has not been completed."
        )

    if match_result.status != "MATCHED":
        raise HTTPException(
            status_code=403,
            detail=(
                "Interview is available only "
                "after successful job matching."
            )
        )

    questions = get_job_questions(
        application,
        db,
    )

    if not questions:
        raise HTTPException(
            status_code=409,
            detail="No interview questions are available."
        )

    existing = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.application_id
            == application.id
        )
        .first()
    )

    if existing:
        current_question = None

        if (
            existing.current_question_index
            < len(questions)
        ):
            current_question = questions[
                existing.current_question_index
            ]

        return {
            "session_id": existing.id,
            "application_id": application.id,
            "status": existing.status,
            "question_id": (
                current_question.id
                if current_question
                else None
            ),
            "question": (
                current_question.question_text
                if current_question
                else None
            ),
            "competency": (
                current_question.competency
                if current_question
                else None
            ),
        }

    session = InterviewSession(
        application_id=application.id,
        status="IN_PROGRESS",
        current_question_index=0,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    first_question = questions[0]

    return {
        "session_id": session.id,
        "application_id": application.id,
        "status": "IN_PROGRESS",
        "question_id": first_question.id,
        "question": first_question.question_text,
        "competency": first_question.competency,
    }


# ============================================================
# NEXT QUESTION
# ============================================================

@router.get("/{session_id}/next-question")
def next_question(
    session_id: int,
    current_user: User = Depends(
        require_role("candidate")
    ),
    db: Session = Depends(get_db),
):
    session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.id == session_id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    if (
        session.application.candidate.user_id
        != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot access this interview."
        )

    questions = get_job_questions(
        session.application,
        db,
    )

    if (
        session.current_question_index
        >= len(questions)
    ):
        return {
            "session_id": session.id,
            "question_id": None,
            "question": None,
            "competency": None,
            "difficulty": None,
            "status": "COMPLETED",
        }

    question = questions[
        session.current_question_index
    ]

    return {
        "session_id": session.id,
        "question_id": question.id,
        "question": question.question_text,
        "competency": question.competency,
        "difficulty": question.difficulty,
        "status": session.status,
    }


# ============================================================
# EVALUATE ANSWER WITH GEMINI
# ============================================================

def evaluate_answer(
    question: Question,
    answer: str,
) -> dict:

    prompt = f"""
You are evaluating a candidate's answer in a structured
professional interview.

Question:
{question.question_text}

Competency:
{question.competency}

Candidate answer:
{answer}

Evaluate only the candidate answer.

Return valid JSON with exactly these fields:

demonstrated_concepts:
list of concepts clearly demonstrated

missing_concepts:
list of important concepts missing from the answer

evidence:
specific evidence from the candidate answer

rubric_level:
one of:
0
1
2
3
4

feedback:
short constructive feedback

Rules:

0 = no meaningful answer or completely incorrect

1 = very limited understanding

2 = partial understanding

3 = good understanding

4 = strong and complete understanding

Do not invent evidence that is not present in the answer.
"""

    try:
        return llm.generate_structured(
            prompt
        )
    except Exception:
        return {
            "demonstrated_concepts": [],
            "missing_concepts": [],
            "evidence": (
                "AI evaluation was unavailable."
            ),
            "rubric_level": 0,
            "feedback": (
                "The answer could not be automatically evaluated."
            ),
        }


# ============================================================
# SUBMIT ANSWER
# ============================================================

@router.post("/{session_id}/answer")
def submit_answer(
    session_id: int,
    question_id: int,
    answer: str,
    current_user: User = Depends(
        require_role("candidate")
    ),
    db: Session = Depends(get_db),
):
    session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.id == session_id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    if (
        session.application.candidate.user_id
        != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot access this interview."
        )

    if session.status == "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail="Interview has already been completed."
        )

    if not answer.strip():
        raise HTTPException(
            status_code=422,
            detail="Answer cannot be empty."
        )

    question = (
        db.query(Question)
        .filter(
            Question.id == question_id
        )
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found."
        )

    questions = get_job_questions(
        session.application,
        db,
    )

    if (
        session.current_question_index
        >= len(questions)
    ):
        raise HTTPException(
            status_code=409,
            detail="There are no remaining questions."
        )

    expected_question = questions[
        session.current_question_index
    ]

    if expected_question.id != question.id:
        raise HTTPException(
            status_code=409,
            detail="This is not the current interview question."
        )

    existing_answer = (
        db.query(InterviewAnswer)
        .filter(
            InterviewAnswer.session_id
            == session.id,
            InterviewAnswer.question_id
            == question.id,
        )
        .first()
    )

    if existing_answer:
        raise HTTPException(
            status_code=409,
            detail="This question has already been answered."
        )

    evaluation = evaluate_answer(
        question,
        answer,
    )

    interview_answer = InterviewAnswer(
        session_id=session.id,
        question_id=question.id,
        answer_text=answer,
        evaluation_json=evaluation,
    )

    db.add(interview_answer)

    session.current_question_index += 1

    next_question = None

    if (
        session.current_question_index
        < len(questions)
    ):
        next_question = questions[
            session.current_question_index
        ]
    else:
        session.status = "COMPLETED"
        session.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(interview_answer)

    if session.status == "COMPLETED":
        report = build_interview_report(
            session,
            db,
        )

        session.final_report_json = report

        db.commit()

    return {
        "session_id": session.id,
        "question_id": question.id,
        "evaluation": evaluation,
        "next_question_id": (
            next_question.id
            if next_question
            else None
        ),
        "next_question": (
            next_question.question_text
            if next_question
            else None
        ),
        "status": session.status,
    }


# ============================================================
# BUILD FINAL REPORT
# ============================================================

def build_interview_report(
    session: InterviewSession,
    db: Session,
) -> dict:

    answers = (
        db.query(InterviewAnswer)
        .filter(
            InterviewAnswer.session_id
            == session.id
        )
        .all()
    )

    competency_data = {}

    for answer in answers:

        question = answer.question
        evaluation = (
            answer.evaluation_json or {}
        )

        competency = question.competency

        if competency not in competency_data:
            competency_data[competency] = {
                "competency": competency,
                "scores": [],
                "answers": [],
            }

        rubric_level = evaluation.get(
            "rubric_level",
            0
        )

        try:
            rubric_level = int(
                rubric_level
            )
        except Exception:
            rubric_level = 0

        competency_data[
            competency
        ]["scores"].append(
            rubric_level
        )

        competency_data[
            competency
        ]["answers"].append({
            "question": question.question_text,
            "answer": answer.answer_text,
            "evaluation": evaluation,
        })

    competency_reports = []

    all_scores = []

    for competency, data in competency_data.items():

        scores = data["scores"]

        average = (
            sum(scores) / len(scores)
            if scores
            else 0
        )

        all_scores.extend(scores)

        competency_reports.append({
            "competency": competency,
            "average_rubric": round(
                average,
                2
            ),
            "max_rubric": 4,
            "answers": data["answers"],
        })

    overall_average = (
        sum(all_scores) / len(all_scores)
        if all_scores
        else 0
    )

    overall_percentage = (
        overall_average / 4 * 100
    )

    return {
        "session_id": session.id,
        "application_id": (
            session.application_id
        ),
        "overall_rubric": round(
            overall_average,
            2
        ),
        "overall_percentage": round(
            overall_percentage,
            2
        ),
        "total_questions": len(answers),
        "competencies": competency_reports,
    }


# ============================================================
# COMPLETE INTERVIEW
# ============================================================

@router.post("/{session_id}/complete")
def complete_interview(
    session_id: int,
    current_user: User = Depends(
        require_role("candidate")
    ),
    db: Session = Depends(get_db),
):
    session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.id == session_id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    if (
        session.application.candidate.user_id
        != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot access this interview."
        )

    questions = get_job_questions(
        session.application,
        db,
    )

    answers = (
        db.query(InterviewAnswer)
        .filter(
            InterviewAnswer.session_id
            == session.id
        )
        .all()
    )

    if len(answers) < len(questions):
        raise HTTPException(
            status_code=409,
            detail=(
                "All interview questions must "
                "be answered before completion."
            )
        )

    report = build_interview_report(
        session,
        db,
    )

    session.status = "COMPLETED"
    session.completed_at = datetime.utcnow()
    session.final_report_json = report

    db.commit()

    return {
        "session_id": session.id,
        "application_id": session.application_id,
        "status": "COMPLETED",
        "report": report,
    }


# ============================================================
# GET INTERVIEW REPORT
# ============================================================

@router.get("/{session_id}/report")
def get_interview_report(
    session_id: int,
    current_user: User = Depends(
        require_role("candidate")
    ),
    db: Session = Depends(get_db),
):
    session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.id == session_id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    if (
        session.application.candidate.user_id
        != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot access this report."
        )

    if not session.final_report_json:
        raise HTTPException(
            status_code=404,
            detail="Interview report is not available yet."
        )

    return {
        "session_id": session.id,
        "application_id": session.application_id,
        "status": session.status,
        "report": session.final_report_json,
    }


# ============================================================
# EMPLOYER VIEW OF INTERVIEW REPORT
# ============================================================

@router.get(
    "/employer/{session_id}/report"
)
def employer_interview_report(
    session_id: int,
    current_user: User = Depends(
        require_role("employer")
    ),
    db: Session = Depends(get_db),
):
    session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.id == session_id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    job = session.application.job

    if job.employer.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access this report."
        )

    if not session.final_report_json:
        raise HTTPException(
            status_code=404,
            detail="Interview report is not available yet."
        )

    return {
        "session_id": session.id,
        "application_id": session.application_id,
        "candidate_id": (
            session.application.candidate_id
        ),
        "job_id": job.id,
        "status": session.status,
        "report": session.final_report_json,
    }