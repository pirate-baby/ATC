from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from app.config import settings


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: str = Field(description="Subject (user ID)")
    exp: datetime = Field(description="Expiration time")
    iat: datetime | None = Field(default=None, description="Issued at time")
    iss: str | None = Field(default=None, description="Issuer")
    aud: str | None = Field(default=None, description="Audience")


class CurrentUser(BaseModel):
    """Represents the authenticated user extracted from JWT."""

    id: UUID = Field(description="User unique identifier")
    token_payload: TokenPayload = Field(description="Full JWT payload")


# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(
    description="JWT Bearer token authentication. Pass token as: Bearer <token>",
    auto_error=True,
)

# Optional bearer scheme (doesn't raise error if missing)
optional_bearer_scheme = HTTPBearer(
    description="Optional JWT Bearer token authentication",
    auto_error=False,
)


def decode_jwt_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode.

    Returns:
        TokenPayload with the decoded claims.

    Raises:
        HTTPException: If token is invalid, expired, or fails validation.
    """
    try:
        # Build validation options
        options = {}
        if not settings.jwt_issuer:
            options["verify_iss"] = False
        if not settings.jwt_audience:
            options["verify_aud"] = False

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options=options,
        )

        # Parse required claims
        sub = payload.get("sub")
        exp = payload.get("exp")

        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing expiration claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Convert exp to datetime
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)

        # Check expiration
        if exp_datetime < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Parse optional claims
        iat = payload.get("iat")
        iat_datetime = datetime.fromtimestamp(iat, tz=timezone.utc) if iat else None

        return TokenPayload(
            sub=sub,
            exp=exp_datetime,
            iat=iat_datetime,
            iss=payload.get("iss"),
            aud=payload.get("aud"),
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user from JWT.

    This dependency validates the Bearer token from the Authorization header
    and extracts user information from the JWT payload.

    Args:
        credentials: HTTP Bearer credentials containing the JWT token.

    Returns:
        CurrentUser object with user ID and token payload.

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired.
    """
    token_payload = decode_jwt_token(credentials.credentials)

    try:
        user_id = UUID(token_payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: subject must be a valid UUID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(id=user_id, token_payload=token_payload)


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_bearer_scheme)],
) -> CurrentUser | None:
    """
    FastAPI dependency to optionally get the current authenticated user.

    Similar to get_current_user but returns None instead of raising
    an exception if no token is provided.

    Args:
        credentials: Optional HTTP Bearer credentials.

    Returns:
        CurrentUser if valid token provided, None otherwise.

    Raises:
        HTTPException: 401 if token is provided but invalid or expired.
    """
    if credentials is None:
        return None

    return await get_current_user(credentials)


async def validate_websocket_token(websocket: WebSocket) -> CurrentUser:
    """
    Validate JWT token from WebSocket query parameter.

    WebSocket connections cannot use HTTP headers for authentication,
    so the token is passed as a query parameter: ?token={jwt}

    Args:
        websocket: The WebSocket connection.

    Returns:
        CurrentUser if token is valid.

    Raises:
        WebSocketException: If token is missing, invalid, or expired.
                          Connection will be closed with 1008 (Policy Violation).
    """
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        raise WebSocketAuthError("Missing authentication token")

    try:
        token_payload = decode_jwt_token(token)
        user_id = UUID(token_payload.sub)
        return CurrentUser(id=user_id, token_payload=token_payload)
    except HTTPException as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.detail)
        raise WebSocketAuthError(e.detail)
    except ValueError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid user ID in token"
        )
        raise WebSocketAuthError("Invalid user ID in token")


class WebSocketAuthError(Exception):
    """Exception raised when WebSocket authentication fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# Type alias for dependency injection
RequireAuth = Annotated[CurrentUser, Depends(get_current_user)]
OptionalAuth = Annotated[CurrentUser | None, Depends(get_optional_current_user)]
