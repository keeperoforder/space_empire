"""Persistent 20-system galaxy, exploration unlocks and expedition rewards."""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path


try:
    _progression_balance = json.loads((Path(__file__).resolve().parents[1] / "balance" / "progression_balance.json").read_text(encoding="utf-8"))
except (OSError, ValueError, TypeError):
    _progression_balance = {}


class GalaxyManager:
    REWARDS = {key: tuple(value) for key, value in _progression_balance.get("expedition", {}).get("rewards", {
        "metal": [70, 150], "crystals": [8, 24], "fuel": [15, 40],
        "credits": [80, 180], "science": [12, 35],
    }).items()}

    def __init__(self, resources, catalog_path=None):
        self.resources = resources
        path = Path(catalog_path) if catalog_path else Path(__file__).with_name("galaxy_catalog.json")
        self.systems = {s["id"]: copy.deepcopy(s) for s in json.loads(path.read_text(encoding="utf-8"))["systems"]}
        self.selected_system = "sol"
        self.plotted_routes = []
        self.expeditions = {}
        self.completed_expeditions = []
        self.trade_routes = [("sol", "vega"), ("sol", "sirius")]
        self.events = []
        self._refresh_accessibility()

    def _refresh_accessibility(self):
        for system in self.systems.values():
            system["accessible"] = system["discovered"] or any(
                self.systems[n]["discovered"] for n in system["neighbors"])

    def get_system(self, system_id):
        return self.systems[system_id]

    def available_scouts(self, fleet):
        return [s for s in fleet.ships if s.ship_type == "scout" and
                s.status == "ready" and s.task == "idle"]

    def route_distance(self, start_id, end_id):
        a, b = self.systems[start_id], self.systems[end_id]
        return math.hypot(a["x"]-b["x"], a["y"]-b["y"])

    def route_time(self, start_id, end_id, speed, scan_seconds=45.0):
        if speed <= 0:
            raise ValueError("speed must be positive")
        return 2.0*self.route_distance(start_id,end_id)/speed + scan_seconds

    def plot_route(self, start_id, end_id):
        if start_id == end_id:
            return False, "Початкова та кінцева системи збігаються."
        if start_id not in self.systems or end_id not in self.systems:
            return False, "Невідома зоряна система."
        if not self.systems[start_id]["discovered"] or not self.systems[end_id]["accessible"]:
            return False, "Маршрут доступний лише до відкритої або сусідньої системи."
        route = {"from": start_id, "to": end_id}
        if route not in self.plotted_routes:
            self.plotted_routes.append(route)
        return True, "Маршрут прокладено."

    def launch_expedition(self, fleet, system_id, ship_id=None):
        target = self.systems[system_id]
        if target["discovered"] or not target["accessible"]:
            return False, "Ця система вже досліджена або ще недоступна."
        scouts = self.available_scouts(fleet)
        ship = next((s for s in scouts if ship_id is None or s.id == ship_id), None)
        if ship is None:
            return False, "Потрібен вільний розвідувальний корабель."
        distance = self.route_distance("sol", system_id)
        mission_speed = getattr(fleet, "technology_bonuses", {}).get("fleet_mission_speed_multiplier", 1.0)
        expedition_tuning = _progression_balance.get("expedition", {})
        scan_time = (float(expedition_tuning.get("base_scan_seconds", 45.0)) +
                     distance * float(expedition_tuning.get("distance_scan_factor", 0.025))) / mission_speed
        total = self.route_time("sol", system_id, ship.speed, scan_time)
        ok, message = fleet.assign_task(ship.id, "explore", target["x"], target["y"],
                                        target["name"], duration=scan_time)
        if not ok:
            return False, message
        ship.metadata["galaxy_expedition"] = system_id
        self.expeditions[ship.id] = {"ship_id": ship.id, "system_id": system_id,
                                     "started": 0.0, "estimated_seconds": total,
                                     "scan_seconds": scan_time, "state": "outbound"}
        self.events.append(f"Експедиція вирушила до системи {target['name']}.")
        return True, f"Експедиція до {target['name']}: орієнтовно {int(total)} с."

    def update(self, fleet):
        for ship_id, expedition in list(self.expeditions.items()):
            ship = next((s for s in fleet.ships if s.id == ship_id), None)
            if ship is None:
                continue
            expedition["state"] = ship.status
            if ship.status == "ready" and ship.task == "idle" and math.hypot(ship.x, ship.y) > 1.0:
                # A ship that was interrupted by maintenance resumes the return leg.
                ship.task, ship.status = "explore", "returning"
                ship.target_x, ship.target_y, ship.target_name = 0.0, 0.0, "Станція"
                continue
            if ship.status == "ready" and ship.task == "idle":
                system = self.systems[expedition["system_id"]]
                system["discovered"] = True
                # Scan reveals all catalogued objects in the newly discovered system.
                for obj in system["objects"]:
                    obj["revealed"] = True
                reward = {}
                for key, bounds in self.REWARDS.items():
                    # Deterministic per system; no random reward on reload/retry.
                    amount = bounds[0] + (sum(ord(c) for c in system["id"]+key) % (bounds[1]-bounds[0]+1))
                    accepted = self.resources.add(key, amount)
                    reward[key] = accepted
                self.completed_expeditions.append({"system_id": system["id"],
                                                   "ship_id": ship_id, "reward": reward})
                self.events.append(f"Експедиція повернулася: {system['name']}. Об'єкти відкрито.")
                ship.metadata.pop("galaxy_expedition", None)
                del self.expeditions[ship_id]
                self._refresh_accessibility()

    def take_events(self):
        events, self.events = self.events, []
        return events

    def snapshot(self):
        return {"systems": copy.deepcopy(self.systems),
                "selected_system": self.selected_system,
                "plotted_routes": copy.deepcopy(self.plotted_routes),
                "expeditions": copy.deepcopy(self.expeditions),
                "completed_expeditions": copy.deepcopy(self.completed_expeditions)}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        saved = data.get("systems", {})
        for sid, state in saved.items():
            if sid not in self.systems:
                continue
            base = self.systems[sid]
            base["discovered"] = bool(state.get("discovered", base["discovered"]))
            for obj in base["objects"]:
                old = next((o for o in state.get("objects", []) if o.get("id") == obj["id"]), None)
                if old:
                    obj["revealed"] = bool(old.get("revealed", obj["revealed"]))
        self.selected_system = data.get("selected_system", "sol")
        if self.selected_system not in self.systems:
            self.selected_system = "sol"
        self.plotted_routes = [r for r in data.get("plotted_routes", [])
                               if r.get("from") in self.systems and r.get("to") in self.systems]
        self.expeditions = {k:v for k,v in data.get("expeditions", {}).items()
                            if v.get("system_id") in self.systems}
        self.completed_expeditions = copy.deepcopy(data.get("completed_expeditions", []))
        self._refresh_accessibility()
