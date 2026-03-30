from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from shared.schemas.enums import JobStatus, JobType


class JobEnqueue(BaseModel):
    job_type: JobType
    project_id: UUID | None = None
    target_type: str | None = None
    target_id: UUID | None = None
    params: dict | None = None
    max_retries: int = Field(default=3, ge=0, le=10)


class JobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID | None
    job_type: str
    target_type: str | None
    target_id: UUID | None
    status: str
    progress: int
    params: dict | None
    result: dict | None
    error_message: str | None
    error_traceback: str | None
    retry_count: int
    max_retries: int
    arq_job_id: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
