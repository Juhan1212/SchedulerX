from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password_hash: str
    
class UserLogin(BaseModel):
    email: str
    password_hash: str

class UserLogOut(BaseModel):
    email: str
    
class UserTestOut(BaseModel):
    email: str