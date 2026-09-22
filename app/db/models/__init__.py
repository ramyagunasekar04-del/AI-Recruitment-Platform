from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    ForeignKey,
    JSON,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ============================================================
# USER
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    candidate_profile: Mapped["CandidateProfile | None"] = relationship(
        "CandidateProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    employer_profile: Mapped["EmployerProfile | None"] = relationship(
        "EmployerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )


# ============================================================
# CANDIDATE PROFILE
# ============================================================

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    resume_file: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    resume_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    profile_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="candidate_profile"
    )

    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )


# ============================================================
# EMPLOYER PROFILE
# ============================================================

class EmployerProfile(Base):
    __tablename__ = "employer_profiles"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    company_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    company_website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="employer_profile"
    )

    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="employer",
        cascade="all, delete-orphan"
    )


# ============================================================
# JOB
# ============================================================

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer_profiles.id"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    blueprint_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    syllabus_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    final_jd: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    employer: Mapped["EmployerProfile"] = relationship(
        "EmployerProfile",
        back_populates="jobs"
    )

    criteria: Mapped[list["JobCriterion"]] = relationship(
        "JobCriterion",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    syllabus_items: Mapped[list["SyllabusItem"]] = relationship(
        "SyllabusItem",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="job",
        cascade="all, delete-orphan"
    )


# ============================================================
# JOB CRITERION
# ============================================================

class JobCriterion(Base):
    __tablename__ = "job_criteria"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False
    )

    criterion_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    criterion_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    weight: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="criteria"
    )


# ============================================================
# SYLLABUS ITEM
# ============================================================

class SyllabusItem(Base):
    __tablename__ = "syllabus_items"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False
    )

    competency: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    topic: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    weight: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="syllabus_items"
    )

    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="syllabus_item"
    )


# ============================================================
# QUESTION
# ============================================================

class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False
    )

    syllabus_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("syllabus_items.id"),
        nullable=True
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    competency: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    difficulty: Mapped[str] = mapped_column(
        String(50),
        default="medium",
        nullable=False
    )

    is_follow_up_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="questions"
    )

    syllabus_item: Mapped["SyllabusItem | None"] = relationship(
        "SyllabusItem",
        back_populates="questions"
    )

    answers: Mapped[list["InterviewAnswer"]] = relationship(
        "InterviewAnswer",
        back_populates="question"
    )


# ============================================================
# APPLICATION
# ============================================================

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id"),
        nullable=False
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False
    )

    job_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="applications"
    )

    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="applications"
    )

    match_result: Mapped["MatchResult | None"] = relationship(
        "MatchResult",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan"
    )

    interview_session: Mapped["InterviewSession | None"] = relationship(
        "InterviewSession",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan"
    )


# ============================================================
# MATCH RESULT
# ============================================================

class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        unique=True,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    score: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False
    )

    criteria_json: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True
    )

    missing_criteria_json: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True
    )

    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="match_result"
    )


# ============================================================
# INTERVIEW SESSION
# ============================================================

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        unique=True,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="IN_PROGRESS",
        nullable=False
    )

    current_question_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    final_report_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="interview_session"
    )

    answers: Mapped[list["InterviewAnswer"]] = relationship(
        "InterviewAnswer",
        back_populates="session",
        cascade="all, delete-orphan"
    )


# ============================================================
# INTERVIEW ANSWER
# ============================================================

class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id"),
        nullable=False
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"),
        nullable=False
    )

    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    evaluation_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="answers"
    )

    question: Mapped["Question"] = relationship(
        "Question",
        back_populates="answers"
    )