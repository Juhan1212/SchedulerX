from pydantic import BaseModel

class SeedOut(BaseModel):
    user_id: int
    amt: int

class SeedUpdate(BaseModel):
    amt: int
