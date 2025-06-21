# Database model for orders

class Order:
    def __init__(self, ticker: str, amount: float, order_type: str):
        self.ticker = ticker
        self.amount = amount
        self.order_type = order_type
