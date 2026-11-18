"""Central API for all game-economy operations."""
from __future__ import annotations
import math
from .resource import Resource

DEFAULT_RESOURCES = {
    "metal":    dict(name="Метал",     amount=650.0, capacity=5000.0, production=2.4, consumption=0.2, icon="◆", color=(190, 205, 218)),
    "energy":   dict(name="Енергія",   amount=420.0, capacity=2500.0, production=5.0, consumption=1.2, icon="ϟ", color=(244, 190, 91)),
    "crystals": dict(name="Кристали",  amount=180.0, capacity=1500.0, production=0.65, consumption=0.05, icon="✦", color=(75, 205, 244)),
    "fuel":     dict(name="Паливо",    amount=300.0, capacity=2000.0, production=1.1, consumption=0.15, icon="⬡", color=(177, 145, 255)),
    "credits":  dict(name="Кредити",  amount=1200.0, capacity=10000.0, production=3.0, consumption=0.4, icon="$", color=(89, 222, 164)),
    "science":  dict(name="Наука",     amount=90.0, capacity=1200.0, production=0.8, consumption=0.0, icon="⌬", color=(255, 151, 190)),
}


class ResourceManager:
    """Owns resource stockpiles and provides a stable API to game systems.

    API examples:
        economy.can_afford({"metal": 100, "energy": 25})
        economy.spend({"metal": 100, "energy": 25})
        economy.add("crystals", 10)
        economy.set_rates("energy", production=8, consumption=2)
        economy.get("metal").amount
    """
    def __init__(self, initial_resources=None, *, new_game=False):
        if new_game:
            definitions = {
                key: {**data, "amount": 0.0, "production": 0.0, "consumption": 0.0}
                for key, data in DEFAULT_RESOURCES.items()
            }
        else:
            definitions = initial_resources if initial_resources is not None else DEFAULT_RESOURCES
        self.resources = {}
        for key, data in definitions.items():
            self.resources[key] = Resource(key=key, **data)

    def _get(self, key: str) -> Resource:
        try:
            return self.resources[key]
        except KeyError as exc:
            raise KeyError(f"Unknown resource: {key}") from exc

    def get(self, key: str) -> Resource:
        return self._get(key)

    def all(self):
        return self.resources.values()

    def add(self, key: str, quantity: float) -> float:
        return self._get(key).add(quantity)

    def can_afford(self, costs) -> bool:
        """Check a mapping of resource keys to quantities."""
        if not hasattr(costs, "items"):
            raise TypeError("costs must be a mapping of resource keys to quantities")
        return all(self._get(key).can_afford(value) for key, value in costs.items())

    def spend(self, costs) -> bool:
        """Atomically spend a mapping; no resource is deducted on failure."""
        if not hasattr(costs, "items"):
            raise TypeError("costs must be a mapping of resource keys to quantities")
        # Validate every key and value before mutating anything.
        normalized = [(self._get(key), value) for key, value in costs.items()]
        if not all(resource.can_afford(value) for resource, value in normalized):
            return False
        for resource, value in normalized:
            if not resource.spend(value):
                raise RuntimeError("Atomic resource transaction invariant failed")
        return True

    def set_rates(self, key: str, production=None, consumption=None) -> None:
        self._get(key).set_rates(production, consumption)

    def update(self, delta_time: float) -> None:
        try:
            dt = float(delta_time)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("delta_time must be finite and non-negative") from exc
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("delta_time must be finite and non-negative")
        for resource in self.resources.values():
            resource.update(dt)

    def snapshot(self) -> dict:
        return {
            key: {
                "amount": r.amount, "capacity": r.capacity,
                "production": r.production, "consumption": r.consumption,
                "balance": r.balance,
            }
            for key, r in self.resources.items()
        }
