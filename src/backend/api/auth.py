import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.database import get_session, Company, LoginToken, Session, Subscriber

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── In-memory rate limiter: email -> list of timestamps ──────────────────────
_login_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 300  # 5 minutes
_RATE_LIMIT_MAX = 3


def _is_rate_limited(email: str) -> bool:
    now = time.monotonic()
    attempts = _login_attempts[email]
    # Prune old entries
    _login_attempts[email] = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    return len(_login_attempts[email]) >= _RATE_LIMIT_MAX


def _record_attempt(email: str) -> None:
    _login_attempts[email].append(time.monotonic())


# ── Schemas ──────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr


class VerifyRequest(BaseModel):
    token: str


class AuthMessageResponse(BaseModel):
    message: str


class VerifyResponse(BaseModel):
    subscriber_id: str


# ── Auth dependency ──────────────────────────────────────────────────────────


async def get_current_subscriber(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Subscriber:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.execute(
        select(Session)
        .where(Session.token == token, Session.expires_at > datetime.now(timezone.utc))
        .options(
            selectinload(Session.subscriber)
            .selectinload(Subscriber.companies)
            .selectinload(Company.industry)
        )
    )
    sess = result.scalar_one_or_none()
    if sess is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    if not sess.subscriber.is_active:
        raise HTTPException(status_code=403, detail="Subscription is inactive")

    return sess.subscriber


# ── Helper ───────────────────────────────────────────────────────────────────

def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.session_ttl_days * 86400,
        path="/",
    )


async def create_session_for_subscriber(
    subscriber: Subscriber,
    session: AsyncSession,
    response: Response,
) -> str:
    """Create a new session row, set cookie, return subscriber_id as string."""
    token = secrets.token_urlsafe(32)
    db_session = Session(
        subscriber_id=subscriber.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days),
    )
    session.add(db_session)
    await session.flush()
    _set_session_cookie(response, token)
    return str(subscriber.id)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/login", response_model=AuthMessageResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    email = body.email.lower()

    if _is_rate_limited(email):
        # Still return 200 to not leak info
        return AuthMessageResponse(message="If an account exists, a login link has been sent.")

    _record_attempt(email)

    # Look up subscriber — always return same message to prevent enumeration
    result = await session.execute(
        select(Subscriber).where(Subscriber.email == email, Subscriber.is_active == True)
    )
    subscriber = result.scalar_one_or_none()

    if subscriber is not None:
        token = secrets.token_urlsafe(32)
        login_token = LoginToken(
            email=email,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.magic_link_ttl_minutes),
        )
        session.add(login_token)
        await session.commit()

        from backend.services.email import send_magic_link_email
        await send_magic_link_email(email, token)

    return AuthMessageResponse(message="If an account exists, a login link has been sent.")


@router.post("/verify", response_model=VerifyResponse)
async def verify(
    body: VerifyRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(LoginToken).where(LoginToken.token == body.token)
    )
    login_token = result.scalar_one_or_none()

    if login_token is None or login_token.used_at is not None or login_token.expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid or expired login link")

    # Mark as used
    login_token.used_at = now

    # Find subscriber
    result = await session.execute(
        select(Subscriber).where(Subscriber.email == login_token.email, Subscriber.is_active == True)
    )
    subscriber = result.scalar_one_or_none()
    if subscriber is None:
        raise HTTPException(status_code=400, detail="Invalid or expired login link")

    subscriber_id = await create_session_for_subscriber(subscriber, session, response)
    await session.commit()

    return VerifyResponse(subscriber_id=subscriber_id)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    token = request.cookies.get("session")
    if token:
        result = await session.execute(select(Session).where(Session.token == token))
        db_session = result.scalar_one_or_none()
        if db_session:
            await session.delete(db_session)
            await session.commit()

    response.delete_cookie(key="session", path="/")
    return {"message": "Logged out"}


@router.get("/me")
async def me(
    current_subscriber: Subscriber = Depends(get_current_subscriber),
):
    from backend.api.subscriptions import _subscriber_to_response
    return _subscriber_to_response(current_subscriber)
