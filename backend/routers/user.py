import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from backend.db.schemas.user import UserCreate, UserLogin, UserTestOut
from backend.dependencies.auth import get_current_user
from backend.dependencies.injection import get_user_service
from backend.core.security import create_token

router = APIRouter()

logger = logging.getLogger(__name__)

@router.post("/signup", response_model=UserTestOut)
def signup(user: UserCreate, user_service=Depends(get_user_service)):
    if user_service.get_user_by_email(user.email):
        raise HTTPException(status_code=400, detail="이미 가입된 사용자입니다.")
    return user_service.create_user(user)

@router.post("/login")
def login(user: UserLogin, response: Response, user_service=Depends(get_user_service)):
    db_user = user_service.get_user_by_email(user.email)
    if not db_user:
        raise HTTPException(status_code=400, detail="가입되지 않은 사용자입니다.")
    if user.password_hash != db_user.password_hash:
        raise HTTPException(status_code=400, detail="아이디나 비밀번호를 확인하세요.")
    token = create_token({"id": db_user.id, "email": db_user.email})
    response.set_cookie("token", token, httponly=True)
    return {"message": "로그인 성공"}

@router.get("/login/auth")
def login_auth(user_db=Depends(get_current_user)):
    if not user_db:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return {"message": "로그인 인증 성공"}