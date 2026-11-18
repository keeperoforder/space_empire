"""Automatic mining fleet simulation, independent from rendering."""
from __future__ import annotations
from dataclasses import dataclass
import math
import json
from pathlib import Path


try:
    _balance_costs = json.loads((Path(__file__).resolve().parents[1] / "balance" / "economy_costs.json").read_text(encoding="utf-8"))
except (OSError, ValueError, TypeError):
    _balance_costs = {}


ASTEROID_DEFINITIONS = [
    {"id":"asteroid_alpha","name":"Астероїд Альфа","x":-650.0,"y":-330.0,"reserve":4200.0,"richness":1.0},
    {"id":"asteroid_beta","name":"Астероїд Бета","x":720.0,"y":-250.0,"reserve":5600.0,"richness":1.25},
    {"id":"asteroid_gamma","name":"Астероїд Гамма","x":-420.0,"y":560.0,"reserve":3600.0,"richness":0.9},
    {"id":"asteroid_delta","name":"Астероїд Дельта","x":680.0,"y":470.0,"reserve":6800.0,"richness":1.5},
]


@dataclass
class Asteroid:
    id: str
    name: str
    x: float
    y: float
    reserve: float
    max_reserve: float
    richness: float = 1.0


@dataclass
class MiningShip:
    id: str
    x: float = 0.0
    y: float = 0.0
    speed: float = 155.0
    cargo_capacity: float = 120.0
    mining_rate: float = 2.0
    fuel_per_unit: float = 0.018
    cargo: float = 0.0
    task: str = "docked"
    target_id: str = "asteroid_alpha"
    assigned_target_id: str = "asteroid_alpha"
    level_speed: int = 1
    level_capacity: int = 1
    level_mining: int = 1
    trip_fuel_reserved: float = 0.0

    @property
    def cargo_ratio(self):
        return self.cargo / self.cargo_capacity if self.cargo_capacity else 0.0


class MiningManager:
    """Runs ship dispatch, travel, extraction, return and unloading automatically.

    Fuel for a complete round trip is reserved atomically before take-off. This
    prevents a ship from becoming stranded halfway due to a depleted fuel tank.
    """
    SHIP_COST = dict(_balance_costs.get("mining_ship", {"metal": 140, "energy": 35, "crystals": 8, "fuel": 25, "credits": 90, "science": 0}))
    SHIP_TUNING = dict(_balance_costs.get("mining_ship_tuning", {}))
    UPGRADE_BASE = {key: dict(value) for key, value in _balance_costs.get("mining_upgrades", {
        "speed": {"metal": 90, "energy": 25, "crystals": 4, "fuel": 8, "credits": 45, "science": 0},
        "capacity": {"metal": 110, "energy": 20, "crystals": 6, "fuel": 8, "credits": 55, "science": 0},
        "mining": {"metal": 120, "energy": 30, "crystals": 10, "fuel": 10, "credits": 70, "science": 5},
    }).items()}

    def __init__(self, resource_manager, initial_ship_count=1):
        self.resources = resource_manager
        self.asteroids = {
            d["id"]: Asteroid(d["id"], d["name"], d["x"], d["y"],
                              d["reserve"], d["reserve"], d["richness"])
            for d in ASTEROID_DEFINITIONS
        }
        self.ships = []
        self.events = []
        self.delivered_total = 0.0
        self.dispatch_fuel_reserve = 0.0
        self.auto_dispatch_enabled = True
        self.technology_bonuses = {"mining_rate_multiplier": 1.0, "mining_fuel_multiplier": 1.0, "ship_speed_multiplier": 1.0}
        self._applied_ship_speed_multiplier = 1.0
        self._next_ship_number = 1
        for _ in range(initial_ship_count):
            self._create_ship()
        self._dispatch_docked_ships()

    def _create_ship(self):
        ship = MiningShip(
            id=f"miner-{self._next_ship_number:03d}",
            speed=float(self.SHIP_TUNING.get("speed", 155.0)),
            cargo_capacity=float(self.SHIP_TUNING.get("cargo_capacity", 120.0)),
            mining_rate=float(self.SHIP_TUNING.get("mining_rate", 2.0)),
            fuel_per_unit=float(self.SHIP_TUNING.get("fuel_per_unit", 0.018)),
        )
        self._next_ship_number += 1
        self.ships.append(ship)
        return ship

    def build_ship(self):
        if not self.resources.spend(self.SHIP_COST):
            return False, "Недостатньо ресурсів для нового шахтарського корабля."
        ship = self._create_ship()
        self.events.append(f"Побудовано шахтарський корабель {ship.id}.")
        self._dispatch_docked_ships()
        return True, f"Шахтарський корабель {ship.id} готовий."

    def assign_ship(self, ship_id, asteroid_id):
        ship = self._find_ship(ship_id)
        if asteroid_id not in self.asteroids:
            raise KeyError(f"Unknown asteroid: {asteroid_id}")
        # Assignment is queued; an active ship completes its current trip safely.
        ship.assigned_target_id = asteroid_id
        if ship.task == "docked":
            ship.target_id = asteroid_id
            self._try_dispatch(ship)
        return True, f"{ship.id} призначено до {self.asteroids[asteroid_id].name} для наступного рейсу."

    def _find_ship(self, ship_id):
        for ship in self.ships:
            if ship.id == ship_id:
                return ship
        raise KeyError(f"Unknown mining ship: {ship_id}")

    def upgrade_ship(self, ship_id, upgrade):
        ship = self._find_ship(ship_id)
        if upgrade not in self.UPGRADE_BASE:
            raise KeyError(f"Unknown upgrade: {upgrade}")
        level_attr = f"level_{upgrade}"
        level = getattr(ship, level_attr)
        if level >= 5:
            return False, "Досягнуто максимального рівня покращення."
        multiplier = 1.0 + level * 0.8
        cost = {k: math.ceil(v * multiplier) for k, v in self.UPGRADE_BASE[upgrade].items()}
        if not self.resources.spend(cost):
            return False, "Недостатньо ресурсів для покращення корабля."
        setattr(ship, level_attr, level + 1)
        if upgrade == "speed":
            ship.speed *= 1.22
        elif upgrade == "capacity":
            ship.cargo_capacity *= 1.3
        elif upgrade == "mining":
            ship.mining_rate *= 1.35
        self.events.append(f"{ship.id}: покращення {upgrade} до рівня {level+1}.")
        return True, f"Покращення {upgrade} завершено."

    def set_technology_bonuses(self, bonuses):
        speed_multiplier = float(bonuses.get("ship_speed_multiplier", 1.0))
        ratio = speed_multiplier / self._applied_ship_speed_multiplier
        for ship in self.ships:
            ship.speed *= ratio
        self._applied_ship_speed_multiplier = speed_multiplier
        self.technology_bonuses = {
            "mining_rate_multiplier": float(bonuses.get("mining_rate_multiplier", 1.0)),
            "mining_fuel_multiplier": float(bonuses.get("mining_fuel_multiplier", 1.0)),
            "ship_speed_multiplier": speed_multiplier,
        }

    def _round_trip_fuel(self, ship, asteroid):
        distance = math.hypot(asteroid.x, asteroid.y)
        return distance * 2.0 * ship.fuel_per_unit * self.technology_bonuses["mining_fuel_multiplier"]

    def _try_dispatch(self, ship):
        ship.target_id = ship.assigned_target_id
        asteroid = self.asteroids[ship.target_id]
        if asteroid.reserve <= 0:
            candidates = [a for a in self.asteroids.values() if a.reserve > 0]
            if not candidates:
                return False
            asteroid = max(candidates, key=lambda a: a.reserve * a.richness)
            ship.target_id = asteroid.id
        fuel_needed = self._round_trip_fuel(ship, asteroid)
        if self.resources.get("fuel").amount - fuel_needed < self.dispatch_fuel_reserve:
            return False
        if not self.resources.spend({"fuel": fuel_needed}):
            return False
        ship.trip_fuel_reserved = fuel_needed
        ship.task = "outbound"
        self.events.append(f"{ship.id}: виліт до {asteroid.name}.")
        return True

    def _dispatch_docked_ships(self):
        if not self.auto_dispatch_enabled:
            return
        for ship in self.ships:
            if ship.task == "docked" and ship.cargo <= 1e-9:
                self._try_dispatch(ship)

    @staticmethod
    def _move_towards(ship, target_x, target_y, distance):
        dx, dy = target_x - ship.x, target_y - ship.y
        remaining = math.hypot(dx, dy)
        if remaining <= 1e-7 or distance >= remaining:
            ship.x, ship.y = target_x, target_y
            return True
        ratio = distance / remaining
        ship.x += dx * ratio
        ship.y += dy * ratio
        return False

    def update(self, delta_time):
        try:
            dt = float(delta_time)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("delta_time must be finite and non-negative") from exc
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("delta_time must be finite and non-negative")
        if dt == 0:
            return

        for ship in self.ships:
            # Consume the frame in small state transitions, preserving leftover dt
            # when a ship arrives and changes phase mid-frame.
            remaining_dt = dt
            transitions = 0
            while remaining_dt > 1e-9 and transitions < 8:
                transitions += 1
                asteroid = self.asteroids[ship.target_id]
                if ship.task == "outbound":
                    distance_before = math.hypot(asteroid.x-ship.x, asteroid.y-ship.y)
                    arrived = self._move_towards(ship, asteroid.x, asteroid.y,
                                                 ship.speed * remaining_dt)
                    if arrived:
                        travel_time = min(remaining_dt, distance_before / ship.speed)
                        remaining_dt = max(0.0, remaining_dt - travel_time)
                        ship.task = "mining"
                        self.events.append(f"{ship.id}: прибув до {asteroid.name}, почато видобуток.")
                    else:
                        remaining_dt = 0.0
                elif ship.task == "mining":
                    free = max(0.0, ship.cargo_capacity - ship.cargo)
                    available = min(free, asteroid.reserve)
                    if available <= 1e-9:
                        ship.task = "returning"
                        self.events.append(f"{ship.id}: вантаж заповнено, повернення.")
                        continue
                    rate = ship.mining_rate * asteroid.richness * self.technology_bonuses["mining_rate_multiplier"]
                    mined = min(available, rate * remaining_dt)
                    asteroid.reserve = max(0.0, asteroid.reserve - mined)
                    ship.cargo += mined
                    used_time = mined / rate if rate > 0 else remaining_dt
                    remaining_dt = max(0.0, remaining_dt - used_time)
                    if ship.cargo >= ship.cargo_capacity - 1e-8 or asteroid.reserve <= 1e-8:
                        ship.task = "returning"
                        self.events.append(f"{ship.id}: видобуток завершено, повернення до станції.")
                    else:
                        remaining_dt = 0.0
                elif ship.task == "returning":
                    distance_before = math.hypot(ship.x, ship.y)
                    arrived = self._move_towards(ship, 0.0, 0.0, ship.speed * remaining_dt)
                    if arrived:
                        travel_time = min(remaining_dt, distance_before / ship.speed)
                        remaining_dt = max(0.0, remaining_dt - travel_time)
                        accepted = self.resources.add("metal", ship.cargo)
                        self.delivered_total += accepted
                        lost = ship.cargo - accepted
                        ship.cargo = 0.0
                        ship.task = "docked"
                        self.events.append(
                            f"{ship.id}: доставлено {accepted:.1f} металу."
                            + (f" Переповнення складу: {lost:.1f}." if lost > 1e-6 else "")
                        )
                    else:
                        remaining_dt = 0.0
                elif ship.task == "docked":
                    # Retry automatically only while the automation policy is enabled.
                    if self.auto_dispatch_enabled:
                        self._try_dispatch(ship)
                    if ship.task == "docked":
                        remaining_dt = 0.0
                else:
                    raise RuntimeError(f"Invalid mining ship task: {ship.task}")

        self._dispatch_docked_ships()

    def take_events(self):
        events, self.events = self.events, []
        return events

    def snapshot(self):
        return {
            "ships": [{
                "id": s.id, "task": s.task, "target_id": s.target_id,
                "assigned_target_id": s.assigned_target_id,
                "x": s.x, "y": s.y, "speed": s.speed,
                "cargo": s.cargo, "cargo_capacity": s.cargo_capacity,
                "mining_rate": s.mining_rate,
                "level_speed": s.level_speed,
                "level_capacity": s.level_capacity,
                "level_mining": s.level_mining,
            } for s in self.ships],
            "asteroids": [{
                "id": a.id, "name": a.name, "reserve": a.reserve,
                "max_reserve": a.max_reserve
            } for a in self.asteroids.values()],
            "delivered_total": self.delivered_total,
        }
