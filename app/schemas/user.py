"""User request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=120, examples=["Ada Lovelace"])
    email: EmailStr = Field(examples=["ada@example.com"])


class UserCreate(UserBase):
    # bcrypt hard-limits at 72 bytes; cap here so hashing never truncates silently.
    password: str = Field(min_length=8, max_length=72, examples=["s3cret-pass"])


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
