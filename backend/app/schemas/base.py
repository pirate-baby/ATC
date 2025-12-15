from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    limit: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")


class FieldError(BaseModel):
    field: str = Field(description="Field name")
    message: str = Field(description="Error message")


class StandardError(BaseModel):
    error: str = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    details: dict | None = Field(default=None, description="Additional error details")


class ValidationError(BaseModel):
    error: str = Field(default="validation_error", description="Error code")
    message: str = Field(description="Human-readable error message")
    fields: list[FieldError] = Field(description="Field-specific errors")
