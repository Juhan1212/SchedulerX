from contextvars import ContextVar
from fastapi import HTTPException, Cookie, Depends
from backend.core.security import decode_token
from backend.dependencies.injection import get_user_service

user_ctx: ContextVar[dict] = ContextVar("user_ctx", default={})

def get_current_user(user_service=Depends(get_user_service), token: str = Cookie(default=None)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("id")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    db_user = user_service.get_user_by_email(email)
    if not db_user or db_user.id != user_id:
        raise HTTPException(status_code=401, detail="User not found or mismatched")
    user_ctx.set(payload)
    return db_user