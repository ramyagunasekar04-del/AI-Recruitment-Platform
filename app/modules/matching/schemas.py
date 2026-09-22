from pydantic import BaseModel


class CriterionMatchResponse(BaseModel):
    criterion_id: int
    criterion: str
    criterion_type: str
    weight: int
    status: str
    evidence: str


class MatchResponse(BaseModel):
    application_id: int
    job_id: int
    job_version: int
    status: str
    score: float
    mandatory_score: float
    optional_score: float
    criteria: list[CriterionMatchResponse]
    missing_criteria: list[str]
    unknown_criteria: list[str]