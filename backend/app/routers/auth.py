import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

router = APIRouter()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


class AuthUrlResponse(BaseModel):
    url: str
    state: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class GitHubUser(BaseModel):
    id: int
    login: str
    email: str | None
    name: str | None
    avatar_url: str | None


def _check_github_configured() -> None:
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured",
        )


def _create_jwt_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": user_id, "exp": expire}

    if settings.jwt_issuer:
        to_encode["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        to_encode["aud"] = settings.jwt_audience

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _get_or_create_user(db: Session, github_user: GitHubUser) -> User:
    user = db.scalar(select(User).where(User.git_handle == github_user.login))

    if user:
        user.email = github_user.email or user.email
        user.display_name = github_user.name or user.display_name
        user.avatar_url = github_user.avatar_url
        db.commit()
        db.refresh(user)
        return user

    user = User(
        git_handle=github_user.login,
        email=github_user.email or f"{github_user.login}@github.local",
        display_name=github_user.name,
        avatar_url=github_user.avatar_url,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/auth/github", response_model=AuthUrlResponse)
async def github_auth(
    redirect_uri: str | None = Query(default=None),
):
    """Initiate GitHub OAuth flow. Returns the authorization URL to redirect the user to."""
    _check_github_configured()

    state = secrets.token_urlsafe(32)

    callback_uri = redirect_uri or settings.github_redirect_uri
    if not callback_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No redirect URI configured. Provide redirect_uri or set GITHUB_REDIRECT_URI.",
        )

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": callback_uri,
        "scope": "user:email",
        "state": state,
    }

    url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    return AuthUrlResponse(url=url, state=state)


@router.get("/auth/github/callback", response_model=TokenResponse)
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Handle GitHub OAuth callback. Exchanges code for token and creates/updates user."""
    _check_github_configured()

    callback_uri = redirect_uri or settings.github_redirect_uri
    if not callback_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No redirect URI configured.",
        )

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": callback_uri,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange code for token",
            )

        token_data = token_response.json()
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=token_data.get("error_description", token_data["error"]),
            )

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No access token in response",
            )

        user_response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch GitHub user profile",
            )

        user_data = user_response.json()

    github_user = GitHubUser(
        id=user_data["id"],
        login=user_data["login"],
        email=user_data.get("email"),
        name=user_data.get("name"),
        avatar_url=user_data.get("avatar_url"),
    )

    user = _get_or_create_user(db, github_user)

    jwt_token = _create_jwt_token(str(user.id))
    expires_in = settings.jwt_access_token_expire_minutes * 60

    return TokenResponse(access_token=jwt_token, expires_in=expires_in)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request):
    """Logout endpoint. With JWT-based auth, this is primarily for client-side token clearing."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)
