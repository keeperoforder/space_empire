"""JSON-backed research tree with persistent progress and aggregated effects."""
from __future__ import annotations
from pathlib import Path
import json, math

TECHNOLOGY_EFFECT_DEFAULTS = {
    "energy_production_multiplier": 1.0,
    "energy_capacity_multiplier": 1.0,
    "energy_consumption_multiplier": 1.0,
    "mining_rate_multiplier": 1.0,
    "mining_fuel_multiplier": 1.0,
    "construction_time_multiplier": 1.0,
    "building_cost_multiplier": 1.0,
    "storage_capacity_multiplier": 1.0,
    "ship_hull_multiplier": 1.0,
    "maintenance_multiplier": 1.0,
    "ship_speed_multiplier": 1.0,
    "ship_fuel_multiplier": 1.0,
    "ship_cargo_multiplier": 1.0,
    "habitation_bonus_multiplier": 1.0,
    "colonization_bonus_multiplier": 1.0,
    "fleet_mission_speed_multiplier": 1.0,
    "research_speed_multiplier": 1.0,
    "combat_readiness": 0.0,
}

class TechnologyManager:
    def __init__(self, resources, catalog_path=None, save_path=None):
        base = Path(__file__).parent
        self.catalog_path = Path(catalog_path) if catalog_path else base / "technology_tree.json"
        self.save_path = Path(save_path) if save_path else base / "progress.json"
        self.resources = resources
        data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        self.branches = data["branches"]
        self.technologies = {item["id"]: item for item in data["technologies"]}
        self.active_research = None
        self.research_enabled = True
        self.events = []
        self._last_saved_elapsed = -1
        self.bonuses = dict(TECHNOLOGY_EFFECT_DEFAULTS)
        self._load_progress()
        self._refresh_states()
        self._recalculate_bonuses()

    def _load_progress(self):
        if not self.save_path.exists():
            return
        try:
            saved = json.loads(self.save_path.read_text(encoding="utf-8"))
            for tech_id, state in saved.get("technologies", {}).items():
                if tech_id in self.technologies and state in ("completed", "locked", "available"):
                    self.technologies[tech_id]["state"] = state
            active = saved.get("active_research")
            if active in self.technologies and self.technologies[active]["state"] != "completed":
                self.active_research = {"technology_id": active,
                    "elapsed": max(0.0, float(saved.get("elapsed", 0.0)))}
                self._last_saved_elapsed = int(self.active_research["elapsed"])
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.active_research = None

    def save(self):
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "technologies": {key: item["state"] for key,item in self.technologies.items()},
            "active_research": self.active_research["technology_id"] if self.active_research else None,
            "elapsed": self.active_research["elapsed"] if self.active_research else 0.0,
        }
        temp = self.save_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        temp.replace(self.save_path)

    def _refresh_states(self):
        completed = {key for key,item in self.technologies.items() if item["state"]=="completed"}
        for key,item in self.technologies.items():
            if key in completed:
                continue
            item["state"] = "available" if all(req in completed for req in item["prerequisites"]) else "locked"
        if self.active_research:
            active_id = self.active_research["technology_id"]
            if active_id in self.technologies:
                self.technologies[active_id]["state"] = "researching"

    def _recalculate_bonuses(self):
        self.bonuses = dict(TECHNOLOGY_EFFECT_DEFAULTS)
        for item in self.technologies.values():
            if item["state"] == "completed":
                for key,value in item["bonuses"].items():
                    if key.endswith("_multiplier"):
                        self.bonuses[key] = self.bonuses.get(key,1.0) * float(value)
                    else:
                        self.bonuses[key] = self.bonuses.get(key,0.0) + float(value)

    def set_research_enabled(self, enabled):
        self.research_enabled = bool(enabled)
        if not self.research_enabled:
            self.active_research = None
            for item in self.technologies.values():
                if item["state"] != "completed":
                    item["state"] = "locked"
            self._recalculate_bonuses()
            self.save()
        else:
            self._refresh_states()
            self.save()

    def get(self, technology_id):
        try:
            return self.technologies[technology_id]
        except KeyError as exc:
            raise KeyError(f"Unknown technology: {technology_id}") from exc

    def start_research(self, technology_id):
        item = self.get(technology_id)
        if not self.research_enabled:
            return False, "Наукову програму ще не відновлено. Виконайте поточне навчальне завдання."
        if self.active_research:
            return False, "Інше дослідження вже виконується."
        if item["state"] != "available":
            return False, "Технологія ще заблокована або вже досліджена."
        cost = float(item["science_cost"])
        if not self.resources.spend({"science": cost}):
            return False, "Недостатньо науки."
        self.active_research = {"technology_id": technology_id, "elapsed": 0.0}
        item["state"] = "researching"
        self.events.append(f"Розпочато дослідження: {item['name']}.")
        self.save()
        return True, f"Дослідження «{item['name']}» розпочато."

    def update(self, dt):
        dt = float(dt)
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("delta_time must be finite and non-negative")
        if not self.active_research or dt <= 0:
            return
        item = self.get(self.active_research["technology_id"])
        speed = max(0.01, self.bonuses.get("research_speed_multiplier",1.0))
        self.active_research["elapsed"] = min(float(item["research_time"]),
            self.active_research["elapsed"] + dt * speed)
        elapsed_second = int(self.active_research["elapsed"])
        if elapsed_second > self._last_saved_elapsed:
            self._last_saved_elapsed = elapsed_second
            self.save()
        if self.active_research["elapsed"] + 1e-9 >= float(item["research_time"]):
            item["state"] = "completed"
            self.events.append(f"Дослідження завершено: {item['name']}.")
            self.active_research = None
            self._last_saved_elapsed = -1
            self._refresh_states()
            self._recalculate_bonuses()
            self.save()

    def progress(self):
        if not self.active_research:
            return None
        item = self.get(self.active_research["technology_id"])
        return {"technology_id": item["id"], "elapsed": self.active_research["elapsed"],
                "duration": item["research_time"],
                "ratio": min(1.0,self.active_research["elapsed"]/item["research_time"])}

    def take_events(self):
        events,self.events = self.events,[]
        return events

    def snapshot(self):
        return {"technologies": self.technologies, "active_research": self.progress(),
                "bonuses": dict(self.bonuses)}
