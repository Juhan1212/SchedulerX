from pydantic import BaseModel

class RegisterExchange(BaseModel):
    user_id: int
    uid: str
    api_key: str
    secret_key: str
