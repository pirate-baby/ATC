import re
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, WebSocket, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

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


# Routes that don't require authentication (regex patterns)
PUBLIC_ROUTES = [
    r"^/$",  # Root
    r"^/health$",  # Health check
    r"^/docs$",  # OpenAPI docs
    r"^/redoc$",  # ReDoc
    r"^/openapi\.json$",  # OpenAPI spec
    r"^/api/v1/auth/.*$",  # Future auth routes (login, register, etc.)
]

# Compiled patterns for performance
_PUBLIC_ROUTE_PATTERNS = [re.compile(pattern) for pattern in PUBLIC_ROUTES]


def is_public_route(path: str) -> bool:
    """Check if a path matches any public route pattern."""
    return any(pattern.match(path) for pattern in _PUBLIC_ROUTE_PATTERNS)


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


def extract_token_from_header(authorization: str | None) -> str | None:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces JWT authentication on all routes except public ones.

    Public routes are defined in PUBLIC_ROUTES and include health checks,
    documentation, and authentication endpoints.

    For authenticated requests, the CurrentUser is stored in request.state.user.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip auth for WebSocket connections (handled separately)
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # Skip auth for public routes
        if is_public_route(request.url.path):
            return await call_next(request)

        # Extract and validate token
        authorization = request.headers.get("Authorization")
        token = extract_token_from_header(authorization)

        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authentication credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            token_payload = decode_jwt_token(token)
            user_id = UUID(token_payload.sub)
            current_user = CurrentUser(id=user_id, token_payload=token_payload)
            # Store user in request state for access in route handlers
            request.state.user = current_user
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
                headers=e.headers or {},
            )
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token: subject must be a valid UUID"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)


def get_current_user(request: Request) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user from request state.

    The user is set by AuthMiddleware for all authenticated requests.

    Args:
        request: The FastAPI request object.

    Returns:
        CurrentUser object with user ID and token payload.

    Raises:
        HTTPException: 401 if user is not in request state (shouldn't happen
                      if middleware is properly configured).
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


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
        WebSocketAuthError: If token is missing, invalid, or expired.
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


# Type alias for dependency injection - gets user from request.state
RequireAuth = Annotated[CurrentUser, Depends(get_current_user)]
