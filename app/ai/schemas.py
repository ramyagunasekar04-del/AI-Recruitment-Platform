from pydantic import BaseModel, Field


# ============================================================
# CANDIDATE PROFILE
# ============================================================

class CandidateProfileAI(BaseModel):

    summary: str = ""

    skills: list[str] = Field(
        default_factory=list
    )

    education: list[str] = Field(
        default_factory=list
    )

    experience: list[str] = Field(
        default_factory=list
    )

    projects: list[str] = Field(
        default_factory=list
    )


# ============================================================
# JOB BLUEPRINT
# ============================================================

class JobBlueprintAI(BaseModel):

    role: str = ""

    mandatory_criteria: list[str] = Field(
        default_factory=list
    )

    optional_criteria: list[str] = Field(
        default_factory=list
    )

    skills: list[str] = Field(
        default_factory=list
    )

    experience_requirements: list[str] = Field(
        default_factory=list
    )

    education_requirements: list[str] = Field(
        default_factory=list
    )


# ============================================================
# SYLLABUS
# ============================================================

class SyllabusItemAI(BaseModel):

    competency: str

    topic: str

    weight: int = 1


class SyllabusAI(BaseModel):

    items: list[SyllabusItemAI] = Field(
        default_factory=list
    )


# ============================================================
# QUESTIONS
# ============================================================

class QuestionAI(BaseModel):

    question_text: str

    competency: str

    difficulty: str = "medium"


class QuestionBankAI(BaseModel):

    questions: list[QuestionAI] = Field(
        default_factory=list
    )


# ============================================================
# FINAL JOB DESCRIPTION
# ============================================================

class JobDescriptionAI(BaseModel):

    summary: str = ""

    responsibilities: list[str] = Field(
        default_factory=list
    )

    must_have_criteria: list[str] = Field(
        default_factory=list
    )

    good_to_have_criteria: list[str] = Field(
        default_factory=list
    )

    experience: list[str] = Field(
        default_factory=list
    )

    hiring_process: list[str] = Field(
        default_factory=list
    )


# ============================================================
# INTERVIEW EVALUATION
# ============================================================

class InterviewEvaluationAI(BaseModel):

    demonstrated_concepts: list[str] = Field(
        default_factory=list
    )

    missing_concepts: list[str] = Field(
        default_factory=list
    )

    evidence: str = ""

    rubric_level: int = 0

    feedback: str = ""