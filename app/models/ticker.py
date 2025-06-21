# Database model for common tickers

class Ticker:
    def __init__(self, name: str, is_active: bool):
        self.name = name
        self.is_active = is_active
