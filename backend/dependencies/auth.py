from contextvars import ContextVar
from fastapi import Request, HTTPException, Cookie
from backend.core.security import decode_token

user_ctx: ContextVar[dict] = ContextVar("user_ctx", default={})

def get_current_user(request: Request, token: str = Cookie(default=None)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_ctx.set(payload)
    return payload