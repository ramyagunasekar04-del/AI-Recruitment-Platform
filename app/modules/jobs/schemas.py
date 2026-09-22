from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    title: str = Field(
        min_length=2,
        max_length=255
    )

    description: str = Field(
        min_length=10
    )


class JobBlueprintResponse(BaseModel):
    role: str

    mandatory_criteria: list[str]

    optional_criteria: list[str]

    skills: list[str]

    experience_requirements: list[str]

    education_requirements: list[str]


class JobDescriptionResponse(BaseModel):
    summary: str

    responsibilities: list[str]

    must_have_criteria: list[str]

    good_to_have_criteria: list[str]

    experience: list[str]

    hiring_process: list[str]


class JobResponse(BaseModel):
    id: int

    title: str

    description: str

    status: str

    version: int

    blueprint: JobBlueprintResponse | None

    final_jd: JobDescriptionResponse | None


class SyllabusItemResponse(BaseModel):
    id: int

    competency: str

    topic: str

    weight: int

    display_order: int


class QuestionResponse(BaseModel):
    id: int

    question_text: str

    competency: str

    difficulty: str

    is_follow_up_allowed: bool