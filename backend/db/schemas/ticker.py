from pydantic import BaseModel

class TickerOut(BaseModel):
    name: str
    ex_rate: str | None = None
