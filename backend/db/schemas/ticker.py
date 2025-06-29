from pydantic import BaseModel

class TickerOut(BaseModel):
    name: str