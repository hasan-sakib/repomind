import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.pr_analysis_status import PRAnalysisStatus, PRRiskLevel
from app.models.pull_request_analysis import PullRequestAnalysis


class AffectedComponentPublic(BaseModel):
    name: str
    file_paths: list[str]


class PotentialConcernPublic(BaseModel):
    description: str
    file_path: str | None
    symbol_name: str | None


class RecommendedTestPublic(BaseModel):
    description: str
    existing_test_file: str | None


class ChangedFilePublic(BaseModel):
    path: str
    status: str
    additions: int
    deletions: int


class PullRequestAnalysisPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: PRAnalysisStatus
    head_sha: str
    risk_level: PRRiskLevel | None
    summary: str | None
    affected_components: list[AffectedComponentPublic]
    potential_concerns: list[PotentialConcernPublic]
    recommended_tests: list[RecommendedTestPublic]
    files_analyzed: list[ChangedFilePublic]
    model: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_analysis(cls, analysis: PullRequestAnalysis) -> "PullRequestAnalysisPublic":
        return cls.model_validate(analysis)
