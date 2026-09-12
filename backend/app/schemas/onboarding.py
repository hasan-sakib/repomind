import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.onboarding_guide import OnboardingGuide
from app.models.onboarding_status import OnboardingGuideStatus


class ImportantModulePublic(BaseModel):
    name: str
    path: str
    kind: str
    file_count: int


class RecommendedFilePublic(BaseModel):
    path: str
    label: str
    kind: str
    dependents_count: int


class DependencyPublic(BaseModel):
    name: str
    version: str | None
    ecosystem: str


class SetupStepPublic(BaseModel):
    order: int
    description: str
    command: str | None
    detected_from: str


class DatabaseStructureEntryPublic(BaseModel):
    path: str
    class_name: str
    symbol_type: str


class LearningPathStepPublic(BaseModel):
    step: int
    label: str
    path: str | None
    reason: str


class FaqEntryPublic(BaseModel):
    question: str
    answer: str
    file_paths: list[str]


class OnboardingGuidePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: OnboardingGuideStatus
    commit_sha: str
    architecture_overview: str | None
    common_workflows: str | None
    authentication_flow: str | None
    faq: list[FaqEntryPublic]
    important_modules: list[ImportantModulePublic]
    recommended_files: list[RecommendedFilePublic]
    key_dependencies: list[DependencyPublic]
    dev_setup_steps: list[SetupStepPublic]
    database_structure: list[DatabaseStructureEntryPublic]
    learning_path: list[LearningPathStepPublic]
    model: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_guide(cls, guide: OnboardingGuide) -> "OnboardingGuidePublic":
        return cls.model_validate(guide)


class SetProgressRequest(BaseModel):
    completed: bool
