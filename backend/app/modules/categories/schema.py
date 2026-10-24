from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome não pode ficar vazio.")
        return value


class CategoryCreate(CategoryInput):
    pass


class CategoryUpdate(CategoryInput):
    pass


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    deleted_at: datetime | None
