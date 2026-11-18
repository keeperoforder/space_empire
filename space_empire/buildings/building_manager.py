"""JSON-driven construction, upgrades and economy effects."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import math


@dataclass
class Construction:
    building_id: str
    duration: float
    elapsed: float = 0.0

    @property
    def progress(self):
        return min(1.0, self.elapsed / self.duration) if self.duration > 0 else 1.0


class BuildingManager:
    """Owns completed buildings and parallel construction projects.

    Costs are paid when a project starts. Effects activate only on completion.
    """
    def __init__(self, resource_manager, catalog_path=None):
        self.resources = resource_manager
        path = Path(catalog_path) if catalog_path else Path(__file__).with_name("catalog.json")
        self.catalog = json.loads(path.read_text(encoding="utf-8"))
        self.owned = {"core": [{"level": 1, "instance_id": "core-001"}]}
        self.constructions: list[Construction] = []
        self.completed_events = []
        self.completed_buildings = []
        self._base_rates = {
            key: (res.production, res.consumption, res.capacity)
            for key, res in self.resources.resources.items()
        }
        self.technology_bonuses = {}
        self._recalculate_effects()

    def set_technology_bonuses(self, bonuses):
        self.technology_bonuses = dict(bonuses)
        self._recalculate_effects()

    def definition(self, building_id):
        try:
            return self.catalog[building_id]
        except KeyError as exc:
            raise KeyError(f"Unknown building: {building_id}") from exc

    def available_definitions(self):
        return [d for d in self.catalog.values() if d.get("buildable", False)]

    def instances(self, building_id=None):
        if building_id is not None:
            return self.owned.get(building_id, [])
        return self.owned

    def count(self, building_id):
        return len(self.owned.get(building_id, []))

    def next_upgrade_cost(self, building_id):
        definition = self.definition(building_id)
        instances = self.owned.get(building_id, [])
        if not instances:
            return None
        level = instances[0]["level"]
        if level >= definition["max_level"]:
            return None
        multiplier = 1.65 ** level * self.technology_bonuses.get("building_cost_multiplier", 1.0)
        return {key: math.ceil(value * multiplier) for key, value in definition["cost"].items()}

    def upgrade_time(self, building_id):
        instances = self.owned.get(building_id, [])
        if not instances:
            return None
        return self.definition(building_id)["build_time"] * (1.0 + 0.35 * instances[0]["level"])

    def start_build(self, building_id):
        definition = self.definition(building_id)
        if not definition.get("buildable", False):
            return False, "Цю споруду не можна будувати окремо."
        cost_multiplier = self.technology_bonuses.get("building_cost_multiplier", 1.0)
        cost = {key: math.ceil(value * cost_multiplier) for key,value in definition["cost"].items()}
        if not self.resources.spend(cost):
            return False, "Недостатньо ресурсів для будівництва."
        duration = float(definition["build_time"]) * self.technology_bonuses.get("construction_time_multiplier", 1.0)
        self.constructions.append(Construction(building_id, duration))
        return True, f"Розпочато будівництво: {definition['name']}."

    def start_upgrade(self, building_id):
        definition = self.definition(building_id)
        instances = self.owned.get(building_id, [])
        if not instances:
            return False, "Спочатку побудуйте цю споруду."
        if any(project.building_id == building_id and getattr(project, "is_upgrade", False)
               for project in self.constructions):
            return False, "Покращення цієї споруди вже виконується."
        cost = self.next_upgrade_cost(building_id)
        if cost is None:
            return False, "Досягнуто максимального рівня."
        if not self.resources.spend(cost):
            return False, "Недостатньо ресурсів для покращення."
        duration = float(self.upgrade_time(building_id)) * self.technology_bonuses.get("construction_time_multiplier", 1.0)
        self.constructions.append(Construction(
            building_id, duration, elapsed=0.0
        ))
        # Upgrade projects are distinguished from new builds by a negative
        # duration marker; progress uses its absolute value.
        self.constructions[-1].duration = float(self.upgrade_time(building_id))
        self.constructions[-1].is_upgrade = True
        return True, f"Розпочато покращення: {definition['name']}."

    def update(self, delta_time):
        dt = float(delta_time)
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("delta_time must be finite and non-negative")
        remaining = []
        for project in self.constructions:
            project.elapsed = min(project.duration, project.elapsed + dt)
            if project.progress >= 1.0:
                definition = self.definition(project.building_id)
                if getattr(project, "is_upgrade", False):
                    instance = self.owned[project.building_id][0]
                    instance["level"] += 1
                    self.completed_buildings.append({
                        "building_id": project.building_id,
                        "instance_id": instance["instance_id"],
                        "level": instance["level"],
                        "upgrade": True,
                    })
                    self.completed_events.append(
                        f"{definition['name']} покращено до рівня {instance['level']}."
                    )
                else:
                    instances = self.owned.setdefault(project.building_id, [])
                    instance = {
                        "level": 1,
                        "instance_id": f"{project.building_id}-{len(instances)+1:03d}"
                    }
                    instances.append(instance)
                    self.completed_buildings.append({
                        "building_id": project.building_id,
                        "instance_id": instance["instance_id"],
                        "level": 1,
                    })
                    self.completed_events.append(f"Завершено будівництво: {definition['name']}.")
            else:
                remaining.append(project)
        if len(remaining) != len(self.constructions):
            self.constructions = remaining
            self._recalculate_effects()

    def _recalculate_effects(self):
        production = {key: 0.0 for key in self.resources.resources}
        consumption = {key: 0.0 for key in self.resources.resources}
        capacity = {key: 0.0 for key in self.resources.resources}
        for building_id, instances in self.owned.items():
            definition = self.definition(building_id)
            for instance in instances:
                multiplier = 1.0 + 0.55 * (instance["level"] - 1)
                for key, rate in definition.get("production", {}).items():
                    tech_multiplier = 1.0
                    if building_id == "habitat":
                        tech_multiplier *= self.technology_bonuses.get("habitation_bonus_multiplier", 1.0)
                    production[key] += rate * multiplier * tech_multiplier
                consumption["energy"] += definition.get("energy_consumption", 0.0) * multiplier
                for key, bonus in definition.get("capacity_bonus", {}).items():
                    capacity[key] += bonus * instance["level"]
        for key, resource in self.resources.resources.items():
            base_prod, base_cons, base_cap = self._base_rates[key]
            production_rate = base_prod + production[key]
            consumption_rate = base_cons + consumption[key]
            capacity_value = base_cap + capacity[key]
            if key == "energy":
                production_rate *= self.technology_bonuses.get("energy_production_multiplier", 1.0)
                consumption_rate *= self.technology_bonuses.get("energy_consumption_multiplier", 1.0)
                capacity_value *= self.technology_bonuses.get("energy_capacity_multiplier", 1.0)
            capacity_value *= self.technology_bonuses.get("storage_capacity_multiplier", 1.0)
            resource.set_rates(production=production_rate, consumption=consumption_rate)
            resource.capacity = capacity_value
            resource.amount = min(resource.amount, resource.capacity)

    def take_completed_events(self):
        events, self.completed_events = self.completed_events, []
        return events

    def take_completed_buildings(self):
        completed, self.completed_buildings = self.completed_buildings, []
        return completed

    def progress_snapshot(self):
        result = []
        for project in self.constructions:
            definition = self.definition(project.building_id)
            result.append({
                "name": definition["name"],
                "progress": project.progress,
                "elapsed": project.elapsed,
                "duration": project.duration,
                "upgrade": getattr(project, "is_upgrade", False),
            })
        return result
