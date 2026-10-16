"""Password hashes, access tokens, and the logged-in user behind a request."""
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from .db import SessionDep
from .errors import ApiError
from .tables import User

HASHER = PasswordHash.recommended()  # argon2
# Checked when there is no password to check, so a wrong username takes as long as a wrong password.
DUMMY_HASH = HASHER.hash("no account has this password")
ALGORITHM = "HS256"
MAX_PASSWORD = 128  # characters register accepts
# The most of a login password that is ever normalised: room for any registered password typed decomposed
# (é as e plus an accent doubles its length), while NFKC on 100,000 characters would stall the server.
MAX_LOGIN_TEXT = 4 * MAX_PASSWORD
# auto_error=False: a missing token reaches current_user, which answers in the API's own error format.
bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def normalized(password):
    """The same password however the keyboard composed it (Unicode NFKC), so an é typed two ways still matches."""
    return unicodedata.normalize("NFKC", password)


def hash_password(password):
    return HASHER.hash(normalized(password))


def verify_password(password, hashed):
    """Whether password matches hashed. Always False without a hash (no such user, or a demo user) or for text far
    longer than any registered password, after the same work, so neither answers faster. The cap comes before
    NFKC, which is slow on long text and would stall the server."""
    if not hashed or len(password) > MAX_LOGIN_TEXT:
        HASHER.verify(normalized(password[:MAX_LOGIN_TEXT]), DUMMY_HASH)
        return False
    return HASHER.verify(normalized(password), hashed)


def create_token(user, settings, now=None):
    """A token naming the user by id (sub) and by token_key (key), valid for JWT_EXPIRE_MINUTES."""
    now = now or datetime.now(timezone.utc)
    claims = {"sub": str(user.id), "key": user.token_key,
              "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def read_token(token, settings):
    """The (user id, token key) a token was issued with, or None when it is forged, broken, expired or incomplete."""
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM],
                            options={"require": ["exp", "sub", "key"]})
        return int(claims["sub"]), claims["key"]
    except (jwt.InvalidTokenError, ValueError):
        return None


def token_response(user, settings):
    """What login and demo-login send back."""
    return {"access_token": create_token(user, settings), "token_type": "bearer",
            "expires_in": settings.jwt_expire_minutes * 60}


def current_user(request: Request, token: Annotated[str | None, Depends(bearer)], session: SessionDep):
    """The user the bearer token names; 401 not_authenticated when there is no valid token. The key must match
    too, so a token issued to a deleted account never works for a newer one that got the same id."""
    claims = None if token is None else read_token(token, request.app.state.settings)
    user = None if claims is None else session.get(User, claims[0])
    # A demo session ends as soon as DEMO_MODE is switched off; real accounts are not affected.
    if user is None or user.token_key != claims[1] or (user.is_demo and not request.app.state.settings.demo_mode):
        raise ApiError(401, "not_authenticated", headers={"WWW-Authenticate": "Bearer"})
    return user


# The logged-in user, for any endpoint that needs one.
UserDep = Annotated[User, Depends(current_user)]
