from pydantic import BaseModel, EmailStr, Field

from app.core.security.password import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from app.schemas.organization import OrganizationMembershipPublic
from app.schemas.user import UserPublic


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    full_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class PasswordResetRequestRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class EmailVerificationConfirmRequest(BaseModel):
    token: str


class AuthResponse(BaseModel):
    user: UserPublic


class MeResponse(BaseModel):
    user: UserPublic
    organizations: list[OrganizationMembershipPublic]
