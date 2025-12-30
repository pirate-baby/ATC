"""API routes for Claude subscription token management and pooling."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import RequireAuth
from app.database import get_db
from app.models.claude_token import ClaudeToken as ClaudeTokenModel
from app.models.enums import ClaudeTokenStatus as ClaudeTokenStatusEnum
from app.models.user import User as UserModel
from app.schemas.base import StandardError
from app.schemas.claude_token import (
    ClaudeToken,
    ClaudeTokenCreate,
    ClaudeTokenStatus,
    ClaudeTokenUpdate,
    PoolHealth,
    TokenPoolStats,
    TokenPoolStatus,
    TokenValidationResult,
    UsageDistribution,
)
from app.services.encryption import decrypt_token, encrypt_token, mask_token

router = APIRouter()


def _token_to_response(token: ClaudeTokenModel) -> ClaudeToken:
    """Convert a database model to a response schema with masked token."""
    # Decrypt token to create preview, then mask it
    try:
        plaintext = decrypt_token(token.encrypted_token)
        preview = mask_token(plaintext)
    except ValueError:
        preview = "****[error]"

    return ClaudeToken(
        id=token.id,
        user_id=token.user_id,
        name=token.name,
        status=ClaudeTokenStatus(token.status.value),
        token_preview=preview,
        request_count=token.request_count,
        last_used_at=token.last_used_at,
        rate_limit_reset_at=token.rate_limit_reset_at,
        last_error=token.last_error,
        created_at=token.created_at,
        updated_at=token.updated_at,
    )


@router.get(
    "/claude-tokens/me",
    response_model=ClaudeToken | None,
    summary="Get my Claude token",
    description="Get the current user's Claude subscription token if they have one.",
    responses={
        404: {"model": StandardError, "description": "User has no token"},
    },
)
async def get_my_token(
    current_user: RequireAuth,
    db: Session = Depends(get_db),
) -> ClaudeToken | None:
    """Get the current user's Claude token."""
    token = db.scalar(
        select(ClaudeTokenModel).where(ClaudeTokenModel.user_id == current_user.id)
    )
    if not token:
        return None
    return _token_to_response(token)


@router.post(
    "/claude-tokens",
    response_model=ClaudeToken,
    status_code=status.HTTP_201_CREATED,
    summary="Add Claude token",
    description="Add a Claude subscription token to the pool. Each user can have only one token.",
    responses={
        400: {"model": StandardError, "description": "Invalid token or already have one"},
        409: {"model": StandardError, "description": "User already has a token"},
    },
)
async def create_token(
    token_data: ClaudeTokenCreate,
    current_user: RequireAuth,
    db: Session = Depends(get_db),
) -> ClaudeToken:
    """Add a new Claude token for the current user."""
    # Check if user already has a token
    existing = db.scalar(
        select(ClaudeTokenModel).where(ClaudeTokenModel.user_id == current_user.id)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a token. Use PATCH to update or DELETE to remove it first.",
        )

    # Validate the token format (basic check)
    # Full validation would require testing against Claude API
    token_value = token_data.token.strip()

    # Encrypt the token for storage
    encrypted = encrypt_token(token_value)

    # Create the token record
    new_token = ClaudeTokenModel(
        user_id=current_user.id,
        name=token_data.name,
        encrypted_token=encrypted,
        status=ClaudeTokenStatusEnum.ACTIVE,
        request_count=0,
    )
    db.add(new_token)
    db.flush()

    return _token_to_response(new_token)


@router.patch(
    "/claude-tokens/me",
    response_model=ClaudeToken,
    summary="Update my Claude token",
    description="Update the current user's Claude token name or replace the token value.",
    responses={
        404: {"model": StandardError, "description": "No token found"},
    },
)
async def update_my_token(
    token_data: ClaudeTokenUpdate,
    current_user: RequireAuth,
    db: Session = Depends(get_db),
) -> ClaudeToken:
    """Update the current user's Claude token."""
    token = db.scalar(
        select(ClaudeTokenModel).where(ClaudeTokenModel.user_id == current_user.id)
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have a token. Use POST to add one.",
        )

    # Update fields
    if token_data.name is not None:
        token.name = token_data.name

    if token_data.token is not None:
        # New token provided - encrypt and store
        encrypted = encrypt_token(token_data.token.strip())
        token.encrypted_token = encrypted
        # Reset status and error when token is replaced
        token.status = ClaudeTokenStatusEnum.ACTIVE
        token.last_error = None
        token.rate_limit_reset_at = None

    db.flush()
    return _token_to_response(token)


@router.delete(
    "/claude-tokens/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove my Claude token",
    description="Remove the current user's Claude token from the pool.",
    responses={
        404: {"model": StandardError, "description": "No token found"},
    },
)
async def delete_my_token(
    current_user: RequireAuth,
    db: Session = Depends(get_db),
) -> None:
    """Remove the current user's Claude token."""
    token = db.scalar(
        select(ClaudeTokenModel).where(ClaudeTokenModel.user_id == current_user.id)
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have a token to remove.",
        )

    db.delete(token)
    db.flush()


@router.post(
    "/claude-tokens/validate",
    response_model=TokenValidationResult,
    summary="Validate my token",
    description="Test the current user's token against Claude's API to verify it works.",
    responses={
        404: {"model": StandardError, "description": "No token found"},
    },
)
async def validate_my_token(
    current_user: RequireAuth,
    db: Session = Depends(get_db),
) -> TokenValidationResult:
    """Validate the current user's token by testing against Claude API."""
    token = db.scalar(
        select(ClaudeTokenModel).where(ClaudeTokenModel.user_id == current_user.id)
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have a token to validate.",
        )

    # Decrypt and validate
    try:
        plaintext = decrypt_token(token.encrypted_token)
    except ValueError:
        # Token is corrupted
        token.status = ClaudeTokenStatusEnum.INVALID
        token.last_error = "Token could not be decrypted - may be corrupted"
        db.flush()
        return TokenValidationResult(valid=False, error="Token is corrupted")

    # Test the token against Claude's API
    validation_result = await _validate_claude_token(plaintext)

    # Update token status based on result
    if validation_result.valid:
        token.status = ClaudeTokenStatusEnum.ACTIVE
        token.last_error = None
    else:
        token.status = ClaudeTokenStatusEnum.INVALID
        token.last_error = validation_result.error

    db.flush()
    return validation_result


async def _validate_claude_token(token: str) -> TokenValidationResult:
    """Validate a token by making a test request to Claude's API.

    This uses a minimal request to verify the token works without
    consuming significant quota.
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            # Use a minimal request to test auth
            # We'll try to create a message with max_tokens=1
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": token,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "Hi"}],
                },
                timeout=30.0,
            )

            if response.status_code == 200:
                return TokenValidationResult(valid=True, account_type="claude")
            elif response.status_code == 401:
                return TokenValidationResult(valid=False, error="Invalid API key")
            elif response.status_code == 403:
                return TokenValidationResult(valid=False, error="Token lacks required permissions")
            elif response.status_code == 429:
                # Rate limited - token is valid but rate limited
                return TokenValidationResult(
                    valid=True,
                    error="Token is rate limited - will work after cooldown",
                    account_type="claude",
                )
            else:
                error_body = response.json() if response.content else {}
                error_msg = error_body.get("error", {}).get("message", f"HTTP {response.status_code}")
                return TokenValidationResult(valid=False, error=error_msg)

    except httpx.TimeoutException:
        return TokenValidationResult(valid=False, error="Request timed out")
    except Exception as e:
        return TokenValidationResult(valid=False, error=f"Validation failed: {str(e)}")


@router.get(
    "/claude-tokens/pool/status",
    response_model=TokenPoolStatus,
    summary="Get pool status",
    description="Get the current status of the Claude token pool (anonymized).",
)
async def get_pool_status(
    db: Session = Depends(get_db),
) -> TokenPoolStatus:
    """Get the current status of the token pool."""
    now = datetime.now(timezone.utc)

    # Count tokens by status
    active_count = db.scalar(
        select(func.count(ClaudeTokenModel.id)).where(
            ClaudeTokenModel.status == ClaudeTokenStatusEnum.ACTIVE
        )
    ) or 0

    rate_limited_count = db.scalar(
        select(func.count(ClaudeTokenModel.id)).where(
            ClaudeTokenModel.status == ClaudeTokenStatusEnum.RATE_LIMITED
        )
    ) or 0

    invalid_count = db.scalar(
        select(func.count(ClaudeTokenModel.id)).where(
            ClaudeTokenModel.status.in_([
                ClaudeTokenStatusEnum.INVALID,
                ClaudeTokenStatusEnum.EXPIRED,
            ])
        )
    ) or 0

    total_contributors = db.scalar(
        select(func.count(ClaudeTokenModel.id))
    ) or 0

    # Calculate total requests served
    total_requests = db.scalar(
        select(func.sum(ClaudeTokenModel.request_count))
    ) or 0

    # Find next available time if all tokens are rate limited
    next_available = None
    if active_count == 0 and rate_limited_count > 0:
        # Get the earliest rate_limit_reset_at
        next_reset = db.scalar(
            select(func.min(ClaudeTokenModel.rate_limit_reset_at)).where(
                ClaudeTokenModel.status == ClaudeTokenStatusEnum.RATE_LIMITED,
                ClaudeTokenModel.rate_limit_reset_at > now,
            )
        )
        next_available = next_reset

    # Determine pool health
    if active_count >= 3:
        health = PoolHealth.HEALTHY
    elif active_count >= 1:
        health = PoolHealth.LIMITED
    else:
        health = PoolHealth.EXHAUSTED

    return TokenPoolStatus(
        total_contributors=total_contributors,
        active_tokens=active_count,
        rate_limited_tokens=rate_limited_count,
        invalid_tokens=invalid_count,
        pool_health=health,
        total_requests_served=total_requests,
        next_available_at=next_available,
    )


@router.get(
    "/claude-tokens/pool/stats",
    response_model=TokenPoolStats,
    summary="Get pool statistics",
    description="Get detailed statistics about the token pool including usage distribution.",
)
async def get_pool_stats(
    db: Session = Depends(get_db),
) -> TokenPoolStats:
    """Get detailed pool statistics with usage distribution."""
    # Get base status
    pool_status = await get_pool_status(db)

    # Calculate usage distribution (anonymized buckets)
    # Get all request counts
    request_counts = db.scalars(
        select(ClaudeTokenModel.request_count)
    ).all()

    # Create distribution buckets
    buckets = [
        ("0", 0, 0),
        ("1-10", 1, 10),
        ("11-50", 11, 50),
        ("51-100", 51, 100),
        ("101-500", 101, 500),
        ("500+", 501, float("inf")),
    ]

    distribution = []
    for label, min_val, max_val in buckets:
        count = sum(1 for c in request_counts if min_val <= c <= max_val)
        if count > 0:  # Only include non-empty buckets
            distribution.append(UsageDistribution(bucket=label, count=count))

    # Calculate fairness score (0-1, higher is better)
    # Uses coefficient of variation (lower CV = more fair)
    if len(request_counts) > 1:
        mean_requests = sum(request_counts) / len(request_counts)
        if mean_requests > 0:
            variance = sum((c - mean_requests) ** 2 for c in request_counts) / len(request_counts)
            std_dev = variance ** 0.5
            cv = std_dev / mean_requests
            # Convert CV to 0-1 score (CV of 0 = 1.0, CV of 2+ = 0.0)
            fairness_score = max(0.0, min(1.0, 1.0 - (cv / 2.0)))
        else:
            fairness_score = 1.0  # All zeros is perfectly fair
    else:
        fairness_score = 1.0  # Single token or no tokens is considered fair

    return TokenPoolStats(
        status=pool_status,
        usage_distribution=distribution,
        fairness_score=round(fairness_score, 3),
    )


# =============================================================================
# Token Pool Rotation Service
# =============================================================================

async def get_available_token(db: Session) -> tuple[str, UUID] | None:
    """Get an available token from the pool using fair rotation.

    Returns the decrypted token and its ID, or None if no tokens available.

    The rotation algorithm prioritizes:
    1. Active tokens with lower request counts (fair distribution)
    2. Rate-limited tokens whose reset time has passed

    Args:
        db: Database session

    Returns:
        Tuple of (decrypted_token, token_id) or None if pool exhausted
    """
    now = datetime.now(timezone.utc)

    # First, check for rate-limited tokens that have reset
    reset_tokens = db.scalars(
        select(ClaudeTokenModel).where(
            ClaudeTokenModel.status == ClaudeTokenStatusEnum.RATE_LIMITED,
            ClaudeTokenModel.rate_limit_reset_at <= now,
        )
    ).all()

    for token in reset_tokens:
        token.status = ClaudeTokenStatusEnum.ACTIVE
        token.rate_limit_reset_at = None
    if reset_tokens:
        db.flush()

    # Get the active token with the lowest request count
    token = db.scalar(
        select(ClaudeTokenModel)
        .where(ClaudeTokenModel.status == ClaudeTokenStatusEnum.ACTIVE)
        .order_by(ClaudeTokenModel.request_count.asc())
        .limit(1)
    )

    if not token:
        return None

    # Decrypt and return
    try:
        plaintext = decrypt_token(token.encrypted_token)
        return (plaintext, token.id)
    except ValueError:
        # Token is corrupted, mark as invalid
        token.status = ClaudeTokenStatusEnum.INVALID
        token.last_error = "Token could not be decrypted"
        db.flush()
        # Try again with next token
        return await get_available_token(db)


async def record_token_usage(
    db: Session,
    token_id: UUID,
    success: bool,
    rate_limited: bool = False,
    error_message: str | None = None,
) -> None:
    """Record the result of using a token.

    Args:
        db: Database session
        token_id: ID of the token used
        success: Whether the request succeeded
        rate_limited: Whether the token hit rate limits
        error_message: Error message if failed
    """
    token = db.scalar(
        select(ClaudeTokenModel).where(ClaudeTokenModel.id == token_id)
    )
    if not token:
        return

    token.request_count += 1
    token.last_used_at = datetime.now(timezone.utc)

    if rate_limited:
        token.status = ClaudeTokenStatusEnum.RATE_LIMITED
        # Claude Pro/Max has 5-hour rate limit windows
        token.rate_limit_reset_at = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        # Add 5 hours to next hour boundary
        from datetime import timedelta
        token.rate_limit_reset_at += timedelta(hours=5)
        token.last_error = "Rate limited - will retry after reset"
    elif not success:
        if error_message and ("invalid" in error_message.lower() or "expired" in error_message.lower()):
            token.status = ClaudeTokenStatusEnum.INVALID
        token.last_error = error_message
    else:
        token.last_error = None

    db.flush()
