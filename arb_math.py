from typing import Tuple

def american_to_decimal(american: int) -> float:
    if american > 0:
        return 1.0 + american / 100.0
    else:
        return 1.0 + 100.0 / abs(american)

def is_two_way_arb(d1: float, d2: float) -> bool:
    return (1.0/d1 + 1.0/d2) < 1.0

def compute_equal_profit_stakes(bankroll: float, d1: float, d2: float) -> Tuple[float, float, float]:
    s1 = bankroll * d2 / (d1 + d2)
    s2 = bankroll - s1
    profit = s1 * d1 - bankroll
    return s1, s2, profit
