import re
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, WebSocket, status
from jose import JWTError, jwt
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.config import settings


class TokenPayload(BaseModel):
    sub: str
    exp: datetime


class CurrentUser(BaseModel):
    id: UUID
    token_payload: TokenPayload


PUBLIC_ROUTES = [
    r"^/$",
    r"^/health$",
    r"^/docs$",
    r"^/redoc$",
    r"^/openapi\.json$",
    r"^/api/v1/auth/.*$",
]

_PUBLIC_ROUTE_PATTERNS = [re.compile(pattern) for pattern in PUBLIC_ROUTES]


def _is_public_route(path: str) -> bool:
    return any(pattern.match(path) for pattern in _PUBLIC_ROUTE_PATTERNS)


def _raise_unauthorized(detail: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_jwt_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        sub = payload.get("sub")
        exp = payload.get("exp")

        if not all([sub, exp]):
            _raise_unauthorized("Invalid token: missing required claims")

        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        if exp_datetime < datetime.now(timezone.utc):
            _raise_unauthorized("Token has expired")

        return TokenPayload(sub=sub, exp=exp_datetime)

    except JWTError as e:
        _raise_unauthorized(f"Invalid token: {e}")


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        if _is_public_route(request.url.path):
            return await call_next(request)

        token = _extract_bearer_token(request.headers.get("Authorization"))
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authentication credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            token_payload = decode_jwt_token(token)
            user_id = UUID(token_payload.sub)
            request.state.user = CurrentUser(id=user_id, token_payload=token_payload)
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
    user = getattr(request.state, "user", None)
    if user is None:
        _raise_unauthorized("Not authenticated")
    return user


async def validate_websocket_token(websocket: WebSocket) -> CurrentUser | None:
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return None

    try:
        token_payload = decode_jwt_token(token)
        user_id = UUID(token_payload.sub)
        return CurrentUser(id=user_id, token_payload=token_payload)
    except HTTPException as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.detail)
        return None
    except ValueError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid user ID in token"
        )
        return None


RequireAuth = Annotated[CurrentUser, Depends(get_current_user)]
