"""Ship model and data-driven specifications for the Space Empire fleet."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path

SHIP_TYPES = {
    "miner": {
        "name": "Шахтарський", "role": "Видобуток", "cost": {"metal": 140, "energy": 35, "crystals": 8, "fuel": 25, "credits": 90},
        "build_time": 18, "speed": 105, "hull": 90, "cargo": 120, "fuel_rate": 0.012,
        "maintenance": 0.35, "description": "Спеціалізований корабель для роботи в астероїдних полях.",
        "color": (100, 205, 235), "shape": "industrial"
    },
    "transport": {
        "name": "Транспортний", "role": "Логістика", "cost": {"metal": 190, "energy": 45, "crystals": 5, "fuel": 35, "credits": 130},
        "build_time": 24, "speed": 115, "hull": 130, "cargo": 260, "fuel_rate": 0.014,
        "maintenance": 0.55, "description": "Перевозить вантажі між станцією та віддаленими об'єктами.",
        "color": (92, 220, 170), "shape": "cargo"
    },
    "scout": {
        "name": "Розвідувальний", "role": "Розвідка", "cost": {"metal": 125, "energy": 55, "crystals": 18, "fuel": 30, "credits": 150},
        "build_time": 22, "speed": 190, "hull": 65, "cargo": 25, "fuel_rate": 0.009,
        "maintenance": 0.45, "description": "Швидкий корабель для дослідження секторів і пошуку цілей.",
        "color": (115, 165, 255), "shape": "needle"
    },
    "fighter": {
        "name": "Винищувач", "role": "Ескорт", "cost": {"metal": 210, "energy": 65, "crystals": 16, "fuel": 45, "credits": 190},
        "build_time": 28, "speed": 170, "hull": 115, "cargo": 15, "fuel_rate": 0.013,
        "maintenance": 0.75, "description": "Маневрений бойовий корабель. Бойова логіка буде додана окремо.",
        "color": (245, 125, 125), "shape": "wings"
    },
    "frigate": {
        "name": "Фрегат", "role": "Охорона", "cost": {"metal": 390, "energy": 105, "crystals": 32, "fuel": 70, "credits": 330},
        "build_time": 42, "speed": 125, "hull": 290, "cargo": 45, "fuel_rate": 0.021,
        "maintenance": 1.35, "description": "Багатоцільовий корабель супроводу та охорони.",
        "color": (245, 177, 100), "shape": "arrow"
    },
    "battleship": {
        "name": "Лінкор", "role": "Важкий ескорт", "cost": {"metal": 780, "energy": 220, "crystals": 75, "fuel": 130, "credits": 720},
        "build_time": 75, "speed": 82, "hull": 760, "cargo": 80, "fuel_rate": 0.038,
        "maintenance": 2.8, "description": "Важкий флагманський корпус. Озброєння зарезервоване для майбутньої бойової системи.",
        "color": (205, 130, 245), "shape": "heavy"
    },
    "colonizer": {
        "name": "Колонізатор", "role": "Колонізація", "cost": {"metal": 520, "energy": 160, "crystals": 55, "fuel": 100, "credits": 500},
        "build_time": 60, "speed": 78, "hull": 240, "cargo": 180, "fuel_rate": 0.026,
        "maintenance": 1.6, "description": "Перевозить обладнання та ресурси для заснування колоній.",
        "color": (225, 215, 125), "shape": "colony"
    },
}

# Balance overrides are data-only; ship stats remain in this catalogue while all
# opening-campaign price points are tunable without editing gameplay code.
try:
    _costs_path = Path(__file__).resolve().parents[1] / "balance" / "economy_costs.json"
    _costs_data = json.loads(_costs_path.read_text(encoding="utf-8"))
    for _ship_id, _cost in _costs_data.get("ships", {}).items():
        if _ship_id in SHIP_TYPES:
            SHIP_TYPES[_ship_id]["cost"] = dict(_cost)
    for _ship_id, _tuning in _costs_data.get("ship_tuning", {}).items():
        if _ship_id in SHIP_TYPES:
            for _key, _value in _tuning.items():
                SHIP_TYPES[_ship_id][_key] = _value
except (OSError, ValueError, TypeError):
    pass

@dataclass
class Spaceship:
    id: str
    ship_type: str
    name: str
    x: float = 0.0
    y: float = 0.0
    task: str = "idle"
    status: str = "ready"
    target_x: float = 0.0
    target_y: float = 0.0
    target_name: str = "Станція"
    hull: float = 100.0
    max_hull: float = 100.0
    speed: float = 100.0
    cargo_capacity: float = 0.0
    level: int = 1
    fuel_consumed: float = 0.0
    maintenance_due: float = 0.0
    group_id: Optional[str] = None
    linked_miner_id: Optional[str] = None
    mission_elapsed: float = 0.0
    mission_duration: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def spec(self):
        return SHIP_TYPES[self.ship_type]

    @property
    def health_ratio(self):
        return self.hull / self.max_hull if self.max_hull else 0.0

    def snapshot(self):
        return {"id": self.id, "type": self.ship_type, "name": self.name,
                "task": self.task, "status": self.status, "x": self.x, "y": self.y,
                "hull": self.hull, "max_hull": self.max_hull, "speed": self.speed,
                "level": self.level, "group_id": self.group_id,
                "target": self.target_name, "fuel_consumed": self.fuel_consumed}
