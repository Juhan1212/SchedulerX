import pytest
from decimal import Decimal, ROUND_DOWN
from consumer import round_volume_to_lot_size

@pytest.mark.parametrize(
    "volume, lot_size, expected",
    [
        (24.39024390243902439, 10.0, 20),
        (24.39024390243902439, 1.0, 24),
        (24.39024390243902439, 0.1, 24.3),
        (24.39024390243902439, 0.01, 24.39),
    ]
)
def test_round_volume_to_lot_size(volume, lot_size, expected):
    result = round_volume_to_lot_size(volume, lot_size)
    print(result)
    assert result == expected