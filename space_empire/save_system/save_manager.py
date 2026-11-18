"""Versioned, checksummed JSON saves and deterministic offline simulation."""
from __future__ import annotations
import copy
import hashlib
import hmac
import json
import math
import os
import shutil
import time
import sys
from pathlib import Path
from dataclasses import asdict, fields
from fleet.spaceship import Spaceship
from mining.mining_manager import MiningShip


SAVE_VERSION = 1
MAX_OFFLINE_SECONDS = 8 * 60 * 60


class SaveError(Exception):
    pass


def archive_existing_files(paths, archive_dir, timestamp=None):
    """Copy existing save/state files to a timestamped archive without deleting originals."""
    from datetime import datetime
    archive_dir = Path(archive_dir)
    existing = [Path(path) for path in paths if Path(path).is_file()]
    if not existing:
        return []
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    archived = []
    for source in existing:
        destination = archive_dir / f"{stamp}_{source.name}"
        shutil.copy2(source, destination)
        archived.append(destination)
    return archived


class SaveManager:
    def __init__(self, path="saves/space_empire_save.json", clock=None):
        self.path = Path(path)
        if not self.path.is_absolute():
            if getattr(sys, "frozen", False):
                user_root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "SpaceEmpire"
                self.path = user_root / self.path
            else:
                self.path = Path(__file__).resolve().parent.parent / self.path
        self.backup_path = self.path.with_suffix(self.path.suffix + ".bak")
        self.clock = clock or time.time
        self.last_save_at = 0.0
        self.last_offline_report = None
        self.warnings = []

    @staticmethod
    def _canonical(payload):
        return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")

    @classmethod
    def _seal(cls, payload):
        data = copy.deepcopy(payload)
        data.pop("checksum", None)
        data["checksum"] = hashlib.sha256(cls._canonical(data)).hexdigest()
        return data

    @classmethod
    def _validate(cls, data):
        if not isinstance(data, dict):
            raise SaveError("Корінь JSON має бути об'єктом.")
        if data.get("format_version") != SAVE_VERSION:
            raise SaveError(f"Непідтримувана версія збереження: {data.get('format_version')}.")
        checksum = data.get("checksum")
        if not isinstance(checksum, str):
            raise SaveError("Відсутній контрольний хеш.")
        expected = cls._seal({k: v for k, v in data.items() if k != "checksum"})["checksum"]
        if not hmac.compare_digest(checksum, expected):
            raise SaveError("Контрольна сума не збігається.")
        if not isinstance(data.get("game"), dict) or not isinstance(data.get("saved_at"), (int, float)):
            raise SaveError("Некоректна структура збереження.")
        return True

    def _capture(self, game):
        resources = {k: {"amount": r.amount, "capacity": r.capacity,
                         "production": r.production, "consumption": r.consumption}
                     for k, r in game.economy.resources.items()}
        buildings = {
            "owned": copy.deepcopy(game.buildings.owned),
            "base_rates": copy.deepcopy(game.buildings._base_rates),
            "constructions": [{"building_id": p.building_id, "duration": p.duration,
                               "elapsed": p.elapsed, "is_upgrade": bool(getattr(p, "is_upgrade", False))}
                              for p in game.buildings.constructions],
        }
        mining = game.mining.snapshot()
        mining["next_ship_number"] = game.mining._next_ship_number
        mining["technology_bonuses"] = copy.deepcopy(game.mining.technology_bonuses)
        mining["applied_ship_speed_multiplier"] = game.mining._applied_ship_speed_multiplier
        # Include every dataclass field, including in-flight cargo/fuel reservation.
        mining["ships"] = [asdict(s) for s in game.mining.ships]
        fleet = {
            "ships": [asdict(s) for s in game.fleet.ships],
            "groups": copy.deepcopy(game.fleet.groups),
            "constructions": copy.deepcopy(game.fleet.constructions),
            "next_id": game.fleet._next_id, "next_group": game.fleet._next_group,
            "upkeep_clock": game.fleet._upkeep_clock,
            "technology_bonuses": copy.deepcopy(game.fleet.technology_bonuses),
            "applied_tech": copy.deepcopy(game.fleet._applied_tech),
        }
        technology = {
            "technologies": {key: item["state"] for key, item in game.technology.technologies.items()},
            "active_research": copy.deepcopy(game.technology.active_research),
        }
        return {
            "resources": resources, "buildings": buildings, "mining": mining,
            "fleet": fleet, "technology": technology,
            "station": {"level": int(getattr(game, "station_level", 1)),
                        "constructed_count": game.station.constructed_count},
            "world": {"opened_planets": copy.deepcopy(getattr(game, "opened_planets", [])),
                      "colonies": copy.deepcopy(getattr(game, "colonies", [])),
                      "galaxy": game.galaxy.snapshot() if hasattr(game, "galaxy") else {},
                       "colony_system": game.colony_manager.snapshot() if hasattr(game, "colony_manager") else {},
                      "automation": game.automation_manager.snapshot() if hasattr(game, "automation_manager") else {},
                      "trade": game.trade_manager.snapshot() if hasattr(game, "trade_manager") else {},
                      "campaign": game.campaign_manager.snapshot() if hasattr(game, "campaign_manager") else {},
                      "progression": game.progression.snapshot() if hasattr(game, "progression") else {}},
            "settings": {"fullscreen": bool(game.is_fullscreen),
                         "camera_zoom": float(game.camera.zoom)},
        }

    def save(self, game):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        now = float(self.clock())
        payload = {"format_version": SAVE_VERSION, "saved_at": now,
                   "save_id": getattr(game, "_save_id", None) or hashlib.sha256(
                       f"{now}:{os.getpid()}".encode()).hexdigest()[:16],
                   "game": self._capture(game)}
        sealed = self._seal(payload)
        encoded = json.dumps(sealed, ensure_ascii=False, indent=2, allow_nan=False)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(encoded, encoding="utf-8")
        # Preserve the previous valid generation before replacing the primary.
        if self.path.exists():
            try:
                previous = json.loads(self.path.read_text(encoding="utf-8"))
                self._validate(previous)
                backup_tmp = self.backup_path.with_suffix(self.backup_path.suffix + ".tmp")
                backup_tmp.write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding="utf-8")
                backup_tmp.replace(self.backup_path)
            except Exception:
                pass
        temp.replace(self.path)
        game._save_id = payload["save_id"]
        self.last_save_at = now
        return payload

    def _read_candidate(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self._validate(data)
        return data

    def load(self):
        self.warnings = []
        if self.path.exists():
            try:
                return self._read_candidate(self.path)
            except (OSError, ValueError, SaveError) as exc:
                self.warnings.append(f"Основне збереження пошкоджене: {exc}")
        if self.backup_path.exists():
            try:
                data = self._read_candidate(self.backup_path)
                self.warnings.append("Відновлено резервну копію.")
                return data
            except (OSError, ValueError, SaveError) as exc:
                self.warnings.append(f"Резервна копія також пошкоджена: {exc}")
        return None

    def restore(self, game, payload, apply_offline=True):
        self._validate(payload)
        data = payload["game"]
        for key, state in data["resources"].items():
            if key not in game.economy.resources:
                continue
            resource = game.economy.get(key)
            resource.amount = min(float(state["amount"]), float(state["capacity"]))
            resource.capacity = float(state["capacity"])
            resource.production = float(state["production"])
            resource.consumption = float(state["consumption"])

        bdata = data["buildings"]
        game.buildings.owned = copy.deepcopy(bdata["owned"])
        if isinstance(bdata.get("base_rates"), dict):
            game.buildings._base_rates = {
                key: tuple(values) for key, values in bdata["base_rates"].items()
                if key in game.economy.resources and isinstance(values, (list, tuple)) and len(values) == 3
            }
        from buildings.building_manager import Construction
        game.buildings.constructions = []
        for item in bdata.get("constructions", []):
            project = Construction(item["building_id"], float(item["duration"]), float(item["elapsed"]))
            project.is_upgrade = bool(item.get("is_upgrade", False))
            game.buildings.constructions.append(project)

        mdata = data["mining"]
        for key, saved in mdata.get("asteroids", {}).items() if isinstance(mdata.get("asteroids"), dict) else []:
            if key in game.mining.asteroids:
                game.mining.asteroids[key].reserve = float(saved["reserve"])
        # Snapshot schema from early Stage 7 stored asteroid entries as a list.
        asteroid_rows = mdata.get("asteroids", [])
        if isinstance(asteroid_rows, list):
            for saved in asteroid_rows:
                if saved["id"] in game.mining.asteroids:
                    game.mining.asteroids[saved["id"]].reserve = float(saved["reserve"])
        game.mining.ships = [MiningShip(**{k: v for k, v in row.items()
                                  if k in MiningShip.__dataclass_fields__})
                             for row in mdata.get("ships", [])]
        game.mining._next_ship_number = int(mdata.get("next_ship_number",
            len(game.mining.ships) + 1))
        game.mining.delivered_total = float(mdata.get("delivered_total", 0.0))
        if mdata.get("technology_bonuses"):
            game.mining.technology_bonuses = dict(mdata["technology_bonuses"])
        game.mining._applied_ship_speed_multiplier = float(
            mdata.get("applied_ship_speed_multiplier",
                      game.mining.technology_bonuses.get("ship_speed_multiplier", 1.0)))

        fdata = data["fleet"]
        game.fleet.ships = [Spaceship(**{k: v for k, v in row.items()
                               if k in Spaceship.__dataclass_fields__})
                            for row in fdata.get("ships", [])]
        game.fleet.groups = {g["id"]: copy.deepcopy(g) for g in fdata.get("groups", [])}
        game.fleet.constructions = copy.deepcopy(fdata.get("constructions", []))
        game.fleet._next_id = int(fdata.get("next_id", 1))
        game.fleet._next_group = int(fdata.get("next_group", 1))
        game.fleet._upkeep_clock = float(fdata.get("upkeep_clock", 0.0))
        game.fleet.technology_bonuses = copy.deepcopy(fdata.get("technology_bonuses", {}))
        game.fleet._applied_tech = copy.deepcopy(fdata.get("applied_tech", game.fleet._applied_tech))

        tdata = data["technology"]
        for key, state in tdata.get("technologies", {}).items():
            if key in game.technology.technologies:
                game.technology.technologies[key]["state"] = state
        game.technology.active_research = copy.deepcopy(tdata.get("active_research"))
        game.technology._refresh_states()
        game.technology._recalculate_bonuses()
        game.technology.save()

        game.buildings._recalculate_effects()
        # Restore all technology multipliers after the saved entities are in place.
        game._applied_technology_bonuses = None
        game._apply_technology_bonuses()
        game.station.constructed_count = 0
        game.station.modules = [m for m in game.station.modules if not hasattr(m, "building_id")]
        for building_id, instances in game.buildings.owned.items():
            if building_id == "core":
                continue
            definition = game.buildings.definition(building_id)
            for instance in instances:
                game.station.add_constructed_building(building_id, definition["name"], definition["sprite"])
                for _ in range(max(0, int(instance["level"]) - 1)):
                    game.station.upgrade_constructed_building(building_id)
        station_data = data.get("station", {})
        game.station_level = int(station_data.get("level", 1))
        world = data.get("world", {})
        game.opened_planets = copy.deepcopy(world.get("opened_planets", []))
        game.colonies = copy.deepcopy(world.get("colonies", []))
        if hasattr(game, "galaxy"):
            game.galaxy.restore(world.get("galaxy", {}))
        if hasattr(game, "colony_manager"):
            game.colony_manager.restore(world.get("colony_system", {}))
        if hasattr(game, "automation_manager"):
            game.automation_manager.restore(world.get("automation", {}))
        if hasattr(game, "trade_manager"):
            game.trade_manager.restore(world.get("trade", {}))
        if hasattr(game, "campaign_manager"):
            game.campaign_manager.restore(world.get("campaign", {}))
        if hasattr(game, "progression"):
            game.progression.restore(world.get("progression", {}))
            game.mining.auto_dispatch_enabled = game.progression.is_unlocked("mining")
        settings = data.get("settings", {})
        game.is_fullscreen = bool(settings.get("fullscreen", game.is_fullscreen))
        game.camera.zoom = max(0.45, min(2.2, float(settings.get("camera_zoom", game.camera.zoom))))
        game.screen = game._create_display()
        game._save_id = payload.get("save_id")

        now = float(self.clock())
        elapsed = max(0.0, now - float(payload["saved_at"]))
        offline_seconds = min(elapsed, MAX_OFFLINE_SECONDS)
        # Claim this offline interval before simulating it. If the process is
        # interrupted mid-simulation, the same interval cannot be awarded twice.
        # The trade-off is that an interrupted offline calculation may be lost.
        self.save(game)
        report = self.simulate_offline(game, offline_seconds) if apply_offline else {
            "elapsed_seconds": 0.0, "capped": False, "resources": {}, "events": []}
        report["real_elapsed_seconds"] = elapsed
        report["capped"] = elapsed > MAX_OFFLINE_SECONDS
        report["saved_at"] = float(payload["saved_at"])
        self.last_offline_report = report
        # Persist the completed offline simulation immediately.
        self.save(game)
        return report

    def simulate_offline(self, game, seconds):
        remaining = max(0.0, min(float(seconds), MAX_OFFLINE_SECONDS))
        before = {k: r.amount for k, r in game.economy.resources.items()}
        events = []
        # Small fixed steps preserve capacity clamps and mission/research state
        # transitions. Energy deficit is handled as a station-wide production
        # throttle: when energy is depleted, non-energy output pauses.
        while remaining > 1e-9:
            dt = min(1.0, remaining)
            energy = game.economy.get("energy")
            powered = energy.amount > 1e-9 or energy.balance >= 0.0
            game.technology.update(dt)
            game.buildings.update(dt)
            game.mining.update(dt)
            game.fleet.update(dt)
            if hasattr(game, "galaxy"):
                game.galaxy.update(game.fleet)
            if hasattr(game, "colony_manager"):
                game.colony_manager.update(dt)
            if hasattr(game, "automation_manager"):
                game.automation_manager.update(dt)
            if hasattr(game, "trade_manager"):
                game.trade_manager.update(dt)
            if hasattr(game, "campaign_manager"):
                game.campaign_manager.update(dt)
            # Energy is always simulated. A depleted station with a negative
            # energy balance pauses other stockpile flows until power recovers.
            energy.update(dt)
            if powered:
                for key, resource in game.economy.resources.items():
                    if key != "energy":
                        resource.update(dt)
            remaining -= dt
        game._apply_technology_bonuses()
        for manager in (game.technology, game.buildings, game.mining, game.fleet, getattr(game, "galaxy", None), getattr(game, "colony_manager", None)):
            if manager is None:
                continue
            if hasattr(manager, "take_events"):
                events.extend(manager.take_events())
        after = {k: r.amount for k, r in game.economy.resources.items()}
        changes = {k: round(after[k] - before[k], 3) for k in before}
        return {"elapsed_seconds": min(float(seconds), MAX_OFFLINE_SECONDS),
                "capped": float(seconds) > MAX_OFFLINE_SECONDS,
                "resources": changes, "events": events}
