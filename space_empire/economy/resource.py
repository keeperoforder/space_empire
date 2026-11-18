"""A validated resource stockpile with production and consumption rates."""
from dataclasses import dataclass
import math


def _finite_non_negative(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite non-negative number") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return number


@dataclass
class Resource:
    """Stores one resource and its per-second flow rates.

    `production` and `consumption` are rates, not accumulated quantities.
    The stockpile is always kept in [0, capacity].
    """
    key: str
    name: str
    amount: float
    capacity: float
    production: float = 0.0
    consumption: float = 0.0
    icon: str = "•"
    color: tuple = (218, 234, 247)

    def __post_init__(self):
        if not self.key or not self.name:
            raise ValueError("Resource key and name cannot be empty")
        self.capacity = _finite_non_negative(self.capacity, "capacity")
        self.amount = _finite_non_negative(self.amount, "amount")
        self.production = _finite_non_negative(self.production, "production")
        self.consumption = _finite_non_negative(self.consumption, "consumption")
        if self.amount > self.capacity:
            raise ValueError("Initial amount cannot exceed capacity")

    @property
    def balance(self) -> float:
        return self.production - self.consumption

    @property
    def free_capacity(self) -> float:
        return max(0.0, self.capacity - self.amount)

    def add(self, quantity: float) -> float:
        """Add stock and return the quantity actually accepted."""
        quantity = _finite_non_negative(quantity, "quantity")
        accepted = min(quantity, self.free_capacity)
        self.amount += accepted
        return accepted

    def can_afford(self, quantity: float) -> bool:
        quantity = _finite_non_negative(quantity, "quantity")
        return self.amount + 1e-9 >= quantity

    def spend(self, quantity: float) -> bool:
        """Spend atomically; return False without changing stock if unaffordable."""
        quantity = _finite_non_negative(quantity, "quantity")
        if not self.can_afford(quantity):
            return False
        self.amount = max(0.0, self.amount - quantity)
        return True

    def set_rates(self, production=None, consumption=None) -> None:
        if production is not None:
            self.production = _finite_non_negative(production, "production")
        if consumption is not None:
            self.consumption = _finite_non_negative(consumption, "consumption")

    def update(self, delta_time: float) -> None:
        delta_time = _finite_non_negative(delta_time, "delta_time")
        # Apply both flows over the same simulation interval. Never allow debt.
        net_change = self.balance * delta_time
        self.amount = min(self.capacity, max(0.0, self.amount + net_change))
