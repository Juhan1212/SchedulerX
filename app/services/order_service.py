# Service for managing orders

def create_order(ticker: str, amount: float, order_type: str):
    return {"ticker": ticker, "amount": amount, "order_type": order_type}
