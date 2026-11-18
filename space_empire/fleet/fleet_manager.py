"""Fleet production, missions, groups, upgrades and upkeep; combat intentionally deferred."""
from __future__ import annotations
import math
from .spaceship import Spaceship, SHIP_TYPES

class FleetManager:
    UPGRADE_COST = {"metal": 90, "energy": 35, "crystals": 8, "credits": 75}
    VALID_TASKS = {"patrol", "explore", "transport", "colonize", "escort", "return"}

    def __init__(self, resources, buildings, mining):
        self.resources, self.buildings, self.mining = resources, buildings, mining
        self.ships = []
        self.groups = {}
        self.constructions = []
        self.events = []
        self._next_id = 1
        self._next_group = 1
        self._upkeep_clock = 0.0
        self.technology_bonuses = {}
        self._applied_tech = {"ship_speed_multiplier": 1.0, "ship_hull_multiplier": 1.0,
                              "ship_cargo_multiplier": 1.0, "colonization_bonus_multiplier": 1.0}
        # Existing mining vessels remain owned by MiningManager; fleet entries are
        # linked control/visual records and never run a second extraction simulation.
        for miner in mining.ships:
            self._register_miner(miner)

    def _register_miner(self, miner):
        spec = SHIP_TYPES["miner"]
        ship = Spaceship(miner.id, "miner", f"Шахтар {miner.id}", miner.x, miner.y,
                         task=miner.task, status="active", hull=spec["hull"], max_hull=spec["hull"],
                         speed=spec["speed"] * self.technology_bonuses.get("ship_speed_multiplier", 1.0),
                         cargo_capacity=(spec["cargo_capacity"] if "cargo_capacity" in spec else spec["cargo"]),
                         linked_miner_id=miner.id)
        self.ships.append(ship)
        return ship

    def set_technology_bonuses(self, bonuses):
        previous = self._applied_tech
        keys = ("ship_speed_multiplier", "ship_hull_multiplier", "ship_cargo_multiplier",
                "colonization_bonus_multiplier")
        current = {key: float(bonuses.get(key, 1.0)) for key in keys}
        for ship in self.ships:
            if ship.ship_type == "miner":
                ship.speed *= current["ship_speed_multiplier"] / previous["ship_speed_multiplier"]
            else:
                ship.speed *= current["ship_speed_multiplier"] / previous["ship_speed_multiplier"]
                cargo_old = previous["ship_cargo_multiplier"] * (previous["colonization_bonus_multiplier"] if ship.ship_type == "colonizer" else 1.0)
                cargo_new = current["ship_cargo_multiplier"] * (current["colonization_bonus_multiplier"] if ship.ship_type == "colonizer" else 1.0)
                ship.cargo_capacity *= cargo_new / cargo_old
            hull_ratio = current["ship_hull_multiplier"] / previous["ship_hull_multiplier"]
            ship.max_hull *= hull_ratio
            ship.hull = min(ship.max_hull, ship.hull * hull_ratio)
        self._applied_tech = current
        self.technology_bonuses = dict(bonuses)

    def _find(self, ship_id):
        for ship in self.ships:
            if ship.id == ship_id:
                return ship
        raise KeyError(f"Unknown ship: {ship_id}")

    def _has_hangar(self):
        return self.buildings.count("hangar") > 0

    def build_ship(self, ship_type):
        if ship_type not in SHIP_TYPES:
            raise KeyError(f"Unknown ship type: {ship_type}")
        if not self._has_hangar():
            return False, "Для виробництва флоту спочатку побудуйте ангар."
        spec = SHIP_TYPES[ship_type]
        if not self.resources.spend(spec["cost"]):
            return False, "Недостатньо ресурсів для виробництва корабля."
        duration = float(spec["build_time"]) * self.technology_bonuses.get("construction_time_multiplier", 1.0)
        self.constructions.append({"ship_type": ship_type, "elapsed": 0.0,
                                   "duration": duration})
        self.events.append(f"Розпочато виробництво: {spec['name']}.")
        return True, f"Виробництво {spec['name']} розпочато ({spec['build_time']} с)."

    def upgrade_ship(self, ship_id, stat):
        ship = self._find(ship_id)
        if ship.ship_type == "miner":
            miner_upgrade = {"speed": "speed", "hull": "mining", "cargo": "capacity"}.get(stat)
            if miner_upgrade is None:
                raise KeyError(f"Unknown upgrade: {stat}")
            return self.mining.upgrade_ship(ship.linked_miner_id, miner_upgrade)
        if stat not in ("speed", "hull", "cargo"):
            raise KeyError(f"Unknown upgrade: {stat}")
        if ship.level >= 5:
            return False, "Досягнуто максимального рівня."
        cost = {k: math.ceil(v * (1 + (ship.level-1)*0.85)) for k,v in self.UPGRADE_COST.items()}
        if not self.resources.spend(cost):
            return False, "Недостатньо ресурсів для покращення."
        if stat == "speed":
            ship.speed *= 1.15
        elif stat == "hull":
            ship.max_hull *= 1.2
            ship.hull = min(ship.max_hull, ship.hull + ship.max_hull*0.2)
        else:
            ship.cargo_capacity *= 1.25
        ship.level += 1
        self.events.append(f"{ship.name}: {stat} покращено до рівня {ship.level}.")
        return True, "Покращення встановлено."

    def create_group(self, name, ship_ids):
        unique = list(dict.fromkeys(ship_ids))
        if not name.strip() or not unique:
            return False, "Вкажіть назву групи та хоча б один корабель."
        for ship_id in unique:
            self._find(ship_id)
        group_id = f"group-{self._next_group:03d}"
        self._next_group += 1
        self.groups[group_id] = {"id": group_id, "name": name.strip(), "ship_ids": unique, "mission": "idle"}
        for ship_id in unique:
            self._find(ship_id).group_id = group_id
        self.events.append(f"Створено групу «{name.strip()}» ({len(unique)} кораблів).")
        return True, group_id

    def dispatch_group(self, group_id, task, target_x, target_y, target_name=None, duration=45.0):
        if task not in self.VALID_TASKS:
            raise KeyError(f"Unknown task: {task}")
        group = self.groups[group_id]
        members = [self._find(sid) for sid in group["ship_ids"]]
        if not members:
            return False, "Група порожня."
        # Atomic fuel reservation: all ships either depart or none do.
        fuel = sum(math.hypot(target_x-s.x, target_y-s.y) * 2 * s.spec["fuel_rate"] *
                   self.technology_bonuses.get("ship_fuel_multiplier", 1.0)
                   for s in members if s.ship_type != "miner")
        if not self.resources.spend({"fuel": fuel}):
            return False, "Недостатньо палива для повного маршруту групи."
        for ship in members:
            if ship.ship_type == "miner":
                continue  # Mining vessels use their dedicated asteroid dispatch loop.
            if ship.status == "maintenance":
                continue
            ship.task, ship.status = task, "outbound"
            ship.target_x, ship.target_y = float(target_x), float(target_y)
            ship.target_name = target_name or task.title()
            ship.mission_elapsed = 0.0
            mission_speed = self.technology_bonuses.get("fleet_mission_speed_multiplier", 1.0)
            ship.mission_duration = max(1.0, float(duration) / mission_speed)
            ship.fuel_consumed += math.hypot(target_x-ship.x, target_y-ship.y) * 2 * ship.spec["fuel_rate"] * self.technology_bonuses.get("ship_fuel_multiplier", 1.0)
        group["mission"] = task
        self.events.append(f"Група «{group['name']}» вирушила: {task}.")
        return True, f"Групу «{group['name']}» відправлено на завдання."

    def assign_task(self, ship_id, task, target_x=0.0, target_y=0.0, target_name=None, duration=45.0):
        ship = self._find(ship_id)
        if ship.ship_type == "miner":
            return False, "Шахтарськими кораблями керує система видобутку."
        if task not in self.VALID_TASKS:
            raise KeyError(f"Unknown task: {task}")
        fuel = math.hypot(target_x-ship.x, target_y-ship.y) * 2 * ship.spec["fuel_rate"] * self.technology_bonuses.get("ship_fuel_multiplier", 1.0)
        if not self.resources.spend({"fuel": fuel}):
            return False, "Недостатньо палива для повного маршруту."
        ship.task, ship.status = task, "outbound"
        ship.target_x, ship.target_y = float(target_x), float(target_y)
        ship.target_name = target_name or task.title()
        mission_speed = self.technology_bonuses.get("fleet_mission_speed_multiplier", 1.0)
        ship.mission_elapsed, ship.mission_duration = 0.0, max(1.0, float(duration) / mission_speed)
        ship.fuel_consumed += fuel
        return True, f"{ship.name} вирушив на завдання."

    def _maintenance(self, dt):
        self._upkeep_clock += dt
        if self._upkeep_clock < 1.0:
            return
        ticks = int(self._upkeep_clock)
        self._upkeep_clock -= ticks
        for ship in self.ships:
            if ship.ship_type == "miner":
                continue
            cost = ship.spec["maintenance"] * ticks * self.technology_bonuses.get("maintenance_multiplier", 1.0)
            if self.resources.spend({"credits": cost}):
                ship.maintenance_due = max(0.0, ship.maintenance_due - cost)
                if ship.status == "maintenance":
                    ship.hull = min(ship.max_hull, ship.hull + 2.0 * ticks)
                    if ship.hull >= ship.max_hull * 0.95:
                        ship.status = "ready"
            else:
                ship.maintenance_due += cost
                ship.status = "maintenance"
                ship.task = "idle"
                ship.hull = max(1.0, ship.hull - 0.08 * ticks)

    def update(self, dt):
        dt = float(dt)
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("delta_time must be finite and non-negative")
        self._maintenance(dt)
        remaining_constructions = []
        for project in self.constructions:
            project["elapsed"] = min(project["duration"], project["elapsed"] + dt)
            if project["elapsed"] + 1e-9 >= project["duration"]:
                ship_type = project["ship_type"]
                spec = SHIP_TYPES[ship_type]
                if ship_type == "miner":
                    miner = self.mining._create_ship()
                    self.mining._dispatch_docked_ships()
                    ship = self._register_miner(miner)
                else:
                    ship_id = f"{ship_type}-{self._next_id:03d}"
                    self._next_id += 1
                    ship = Spaceship(ship_id, ship_type, f"{spec['name']} {self._next_id-1:03d}",
                                     hull=spec["hull"] * self.technology_bonuses.get("ship_hull_multiplier", 1.0),
                                     max_hull=spec["hull"] * self.technology_bonuses.get("ship_hull_multiplier", 1.0),
                                     speed=spec["speed"] * self.technology_bonuses.get("ship_speed_multiplier", 1.0),
                                     cargo_capacity=spec["cargo"] * self.technology_bonuses.get("ship_cargo_multiplier", 1.0) *
                                     (self.technology_bonuses.get("colonization_bonus_multiplier", 1.0)
                                      if ship_type == "colonizer" else 1.0))
                    self.ships.append(ship)
                self.events.append(f"Корабель готовий: {ship.name}.")
            else:
                remaining_constructions.append(project)
        self.constructions = remaining_constructions
        for ship in self.ships:
            if ship.ship_type == "miner":
                miner = next((m for m in self.mining.ships if m.id == ship.linked_miner_id), None)
                if miner:
                    ship.x, ship.y, ship.task = miner.x, miner.y, miner.task
                    ship.status = "active" if miner.task != "docked" else "ready"
                continue
            if ship.status == "maintenance" or ship.task == "idle":
                continue
            remaining = dt
            transitions = 0
            while remaining > 1e-9 and transitions < 6:
                transitions += 1
                if ship.status == "outbound":
                    dx, dy = ship.target_x-ship.x, ship.target_y-ship.y
                    distance = math.hypot(dx,dy)
                    if distance < 1e-6:
                        ship.x, ship.y, ship.status = ship.target_x, ship.target_y, "working"
                        continue
                    travel_time = distance / ship.speed
                    if travel_time <= remaining:
                        ship.x, ship.y, ship.status = ship.target_x, ship.target_y, "working"
                        remaining -= travel_time
                    else:
                        travel = ship.speed * remaining
                        ship.x += dx/distance*travel
                        ship.y += dy/distance*travel
                        remaining = 0.0
                elif ship.status == "working":
                    needed = max(0.0, ship.mission_duration-ship.mission_elapsed)
                    used = min(remaining, needed)
                    ship.mission_elapsed += used
                    remaining -= used
                    if ship.mission_elapsed + 1e-9 >= ship.mission_duration:
                        if ship.metadata.get("trade_route_stage") == "to_source":
                            destination = ship.metadata.get("trade_destination", {})
                            ship.target_x = float(destination.get("x", 0.0))
                            ship.target_y = float(destination.get("y", 0.0))
                            ship.target_name = destination.get("name", "Колонія")
                            ship.metadata["trade_route_stage"] = "to_destination"
                            ship.status = "outbound"
                            ship.mission_elapsed = 0.0
                            ship.mission_duration = 2.0
                        else:
                            ship.status = "returning"
                            ship.target_x, ship.target_y, ship.target_name = 0.0, 0.0, "Станція"
                    else:
                        remaining = 0.0
                elif ship.status == "returning":
                    distance = math.hypot(ship.x,ship.y)
                    if distance < 1e-6:
                        ship.x = ship.y = 0.0
                        ship.status, ship.task = "ready", "idle"
                        self.events.append(f"{ship.name} повернувся на станцію.")
                        remaining = 0.0
                        continue
                    travel_time = distance / ship.speed
                    if travel_time <= remaining:
                        ship.x = ship.y = 0.0
                        ship.status, ship.task = "ready", "idle"
                        self.events.append(f"{ship.name} повернувся на станцію.")
                        remaining -= travel_time
                    else:
                        travel = ship.speed * remaining
                        ship.x -= ship.x/distance*travel
                        ship.y -= ship.y/distance*travel
                        remaining = 0.0
        self._sync_new_miners()

    def _sync_new_miners(self):
        known = {s.linked_miner_id for s in self.ships if s.linked_miner_id}
        for miner in self.mining.ships:
            if miner.id not in known:
                self._register_miner(miner)

    def take_events(self):
        result, self.events = self.events, []
        return result

    def snapshot(self):
        return {"ships": [s.snapshot() for s in self.ships],
                "groups": list(self.groups.values()),
                "constructions": list(self.constructions)}
