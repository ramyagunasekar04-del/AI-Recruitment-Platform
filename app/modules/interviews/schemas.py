from pydantic import BaseModel, Field


class StartInterviewResponse(BaseModel):
    session_id: int
    application_id: int
    status: str
    question_id: int | None
    question: str | None
    competency: str | None


class NextQuestionResponse(BaseModel):
    session_id: int
    question_id: int | None
    question: str | None
    competency: str | None
    difficulty: str | None
    status: str


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(min_length=1)


class InterviewAnswerResponse(BaseModel):
    session_id: int
    question_id: int
    evaluation: dict
    next_question_id: int | None
    next_question: str | None
    status: str


class InterviewReportResponse(BaseModel):
    session_id: int
    application_id: int
    status: str
    report: dict