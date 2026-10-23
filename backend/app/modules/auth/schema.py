from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CredentialsInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class RegistrationInput(CredentialsInput):
    password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UserORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
