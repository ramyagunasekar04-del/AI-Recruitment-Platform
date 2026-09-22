from pydantic import BaseModel, Field


class CandidateProfileResponse(BaseModel):
    id: int
    full_name: str
    phone: str | None
    resume_filename: str | None
    profile: dict | None


class EmployerProfileRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)


class EmployerProfileResponse(BaseModel):
    id: int
    company_name: str