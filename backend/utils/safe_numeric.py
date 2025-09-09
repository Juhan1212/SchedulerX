from decimal import Decimal, ROUND_DOWN

def safe_numeric(value, scale=8, max_value=Decimal('999999999999999999.99999999')):
    """
    DB numeric(18,8) 필드에 안전하게 저장할 수 있도록 값의 범위와 소수점 자릿수를 맞춰줍니다.
    """
    quantize_str = '0.' + '0' * (scale - 1) + '1'
    value = Decimal(str(value)).quantize(Decimal(quantize_str), rounding=ROUND_DOWN)
    if abs(value) > max_value:
        return max_value if value > 0 else -max_value
    return value
