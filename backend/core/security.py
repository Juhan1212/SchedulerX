import os
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("ENCODING_KEY")
if not SECRET_KEY:
    raise ValueError("ENCODING_KEY environment variable is not set")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
if not ALGORITHM:
    raise ValueError("ALGORITHM environment variable is not set")

def create_token(data: dict) -> str:
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is not set")
    
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is not set")
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    