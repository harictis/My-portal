from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import workflow


def normalize_required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Value cannot be blank")
    return value


class AccessRequestCreate(BaseModel):
    user_name: str
    repository: str
    access_type: str
    reason: str

    @field_validator("user_name", "repository", "reason")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("access_type")
    @classmethod
    def validate_access_type(cls, value: str) -> str:
        access_type = workflow.normalize_access_type(value)
        if access_type not in workflow.ACCESS_TYPES:
            raise ValueError("Access type must be read or write")
        return access_type


class AccessRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_name: str
    repository: str
    access_type: str
    reason: str
    status: str
    created_at: datetime


class AccessRequestCreated(BaseModel):
    message: str
    request_id: int


class AccessRequestCancelled(BaseModel):
    message: str
    status: str


class CancelAccessRequest(BaseModel):
    cancelled_by: str
    reason: Optional[str] = None

    @field_validator("cancelled_by")
    @classmethod
    def validate_cancelled_by(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        value = value.strip()
        return value or None
    
class LeadershipApproval(BaseModel):
    approved_by: str
    decision: str

    @field_validator("approved_by")
    @classmethod
    def validate_approved_by(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        decision = workflow.normalize_decision(value)
        if decision not in workflow.LEADERSHIP_DECISIONS:
            raise ValueError("Decision must be approve or reject")
        return decision


class LeadershipApprovalResponse(BaseModel):
    message: str
    status: str
    
class CommentCreate(BaseModel):
    request_id: int = Field(gt=0)
    comment_by: str
    comment_text: str

    @field_validator("comment_by", "comment_text")
    @classmethod
    def validate_comment_text(cls, value: str) -> str:
        return normalize_required_text(value)


class CommentCreated(BaseModel):
    message: str
    comment_id: int


class DevOpsAuthorizationResponse(BaseModel):
    message: str
    team_assigned: str
    status: str
