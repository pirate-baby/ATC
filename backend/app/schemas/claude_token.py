from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ClaudeTokenStatus(str, Enum):
    """Status of a Claude subscription token."""

    ACTIVE = "active"
    INVALID = "invalid"
    RATE_LIMITED = "rate_limited"
    EXPIRED = "expired"


class ClaudeTokenCreate(BaseModel):
    """Schema for creating/adding a new Claude token."""

    name: str = Field(
        description="Friendly name for the token (e.g., 'Personal Account')",
        min_length=1,
        max_length=255,
    )
    token: str = Field(
        description="The Claude OAuth token from 'claude setup-token'",
        min_length=10,  # Tokens are much longer, but this catches obviously bad inputs
    )

    @field_validator("token")
    @classmethod
    def validate_token_format(cls, v: str) -> str:
        """Basic token format validation."""
        v = v.strip()
        if not v:
            raise ValueError("Token cannot be empty")
        # Claude tokens typically start with specific prefixes
        # We'll do full validation by testing against the API later
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean the token name."""
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class ClaudeTokenUpdate(BaseModel):
    """Schema for updating an existing Claude token."""

    name: str | None = Field(
        default=None,
        description="New friendly name for the token",
        min_length=1,
        max_length=255,
    )
    token: str | None = Field(
        default=None,
        description="New token value to replace the existing one",
        min_length=10,
    )

    @field_validator("token")
    @classmethod
    def validate_token_format(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Token cannot be empty")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty")
        return v


class ClaudeToken(BaseModel):
    """Schema for a Claude token (returned to user - no sensitive data)."""

    id: UUID = Field(description="Token unique identifier")
    user_id: UUID = Field(description="Owner user ID")
    name: str = Field(description="Friendly name for the token")
    status: ClaudeTokenStatus = Field(description="Current token status")
    token_preview: str = Field(description="Masked preview of the token (e.g., '****...abc')")
    request_count: int = Field(description="Number of requests served by this token")
    last_used_at: datetime | None = Field(
        default=None, description="When the token was last used"
    )
    rate_limit_reset_at: datetime | None = Field(
        default=None, description="When rate limit resets (if rate limited)"
    )
    last_error: str | None = Field(
        default=None, description="Last error message (if any)"
    )
    created_at: datetime = Field(description="When the token was added")
    updated_at: datetime | None = Field(default=None, description="Last update time")

    model_config = {"from_attributes": True}


class PoolHealth(str, Enum):
    """Overall health status of the token pool."""

    HEALTHY = "healthy"  # Majority of tokens are active
    LIMITED = "limited"  # Some tokens available but pool is constrained
    EXHAUSTED = "exhausted"  # No tokens available


class TokenPoolStatus(BaseModel):
    """Public pool status information (anonymized)."""

    total_contributors: int = Field(description="Number of users with active tokens")
    active_tokens: int = Field(description="Number of currently usable tokens")
    rate_limited_tokens: int = Field(description="Tokens temporarily rate-limited")
    invalid_tokens: int = Field(description="Tokens that need attention")
    pool_health: PoolHealth = Field(description="Overall pool health status")
    total_requests_served: int = Field(description="Total requests served by the pool")
    next_available_at: datetime | None = Field(
        default=None,
        description="If all tokens rate-limited, when the next one becomes available",
    )


class UsageDistribution(BaseModel):
    """Anonymized usage distribution for fairness visualization."""

    bucket: str = Field(description="Usage bucket (e.g., '0-100', '100-500')")
    count: int = Field(description="Number of contributors in this bucket")


class TokenPoolStats(BaseModel):
    """Extended pool statistics for dashboard."""

    status: TokenPoolStatus = Field(description="Current pool status")
    usage_distribution: list[UsageDistribution] = Field(
        description="Anonymized distribution of usage across contributors"
    )
    fairness_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score from 0-1 indicating how fairly usage is distributed (1 = perfectly fair)",
    )


class TokenValidationResult(BaseModel):
    """Result of validating a token against Claude's API."""

    valid: bool = Field(description="Whether the token is valid")
    error: str | None = Field(default=None, description="Error message if invalid")
    account_type: str | None = Field(
        default=None, description="Account type if valid (e.g., 'pro', 'max')"
    )
