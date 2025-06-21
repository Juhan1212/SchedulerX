from typing import Optional

# Database model for positions

class Position:
    def __init__(self, ticker: str, entry_price: float, exit_price: Optional[float] = None):
        self.ticker = ticker
        self.entry_price = entry_price
        self.exit_price = exit_price
