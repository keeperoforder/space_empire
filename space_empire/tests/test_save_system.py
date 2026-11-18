import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from save_system.save_manager import SaveManager, SaveError, archive_existing_files, MAX_OFFLINE_SECONDS
from economy import ResourceManager
from buildings import BuildingManager
from mining import MiningManager
from fleet import FleetManager
from technology import TechnologyManager


class FakeResource:
    def __init__(self, amount, production=1.0, consumption=0.0, capacity=100000):
        self.amount, self.production, self.consumption, self.capacity = amount, production, consumption, capacity
    @property
    def balance(self):
        return self.production - self.consumption
    def update(self, dt):
        self.amount = min(self.capacity, max(0.0, self.amount + self.balance * dt))


class FakeManager:
    def __init__(self):
        self.elapsed = 0.0
        self.events = []
    def update(self, dt):
        self.elapsed += dt
    def take_events(self):
        result, self.events = self.events, []
        return result




class FakeStation:
    def __init__(self):
        self.constructed_count = 0
        self.modules = []
    def add_constructed_building(self, *args):
        self.constructed_count += 1
    def upgrade_constructed_building(self, *args):
        return True


class FakeGame:
    def __init__(self, tmp):
        self.economy = ResourceManager()
        self.buildings = BuildingManager(self.economy)
        self.mining = MiningManager(self.economy, initial_ship_count=0)
        self.fleet = FleetManager(self.economy, self.buildings, self.mining)
        self.technology = TechnologyManager(
            self.economy,
            save_path=Path(tmp) / "technology_progress.json")
        self.station = FakeStation()
        self.station_level = 1
        self.opened_planets = []
        self.colonies = []
        self.is_fullscreen = False
        self.camera = SimpleNamespace(zoom=1.0)
        self._save_id = None
        self._applied_technology_bonuses = None
        self.screen = None
    def _create_display(self):
        return None
    def _apply_technology_bonuses(self):
        bonuses = dict(self.technology.bonuses)
        if bonuses != self._applied_technology_bonuses:
            self.buildings.set_technology_bonuses(bonuses)
            self.mining.set_technology_bonuses(bonuses)
            self.fleet.set_technology_bonuses(bonuses)
            self._applied_technology_bonuses = bonuses

class SaveSystemTests(unittest.TestCase):
    def test_checksum_validation_and_tamper_detection(self):
        payload = SaveManager._seal({"format_version": 1, "saved_at": 10, "game": {}})
        self.assertTrue(SaveManager._validate(payload))
        payload["saved_at"] = 11
        with self.assertRaises(SaveError):
            SaveManager._validate(payload)

    def test_version_validation(self):
        payload = SaveManager._seal({"format_version": 99, "saved_at": 10, "game": {}})
        with self.assertRaises(SaveError):
            SaveManager._validate(payload)

    def test_corrupt_primary_falls_back_to_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SaveManager(Path(tmp) / "save.json")
            valid = SaveManager._seal({"format_version": 1, "saved_at": 10, "game": {}})
            manager.backup_path.write_text(json.dumps(valid), encoding="utf-8")
            manager.path.write_text("{broken", encoding="utf-8")
            loaded = manager.load()
            self.assertEqual(loaded["saved_at"], 10)
            self.assertTrue(any("резерв" in warning.lower() for warning in manager.warnings))

    def test_restore_commits_offline_interval_and_prevents_duplicate_award(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = [1000.0]
            game = FakeGame(tmp)
            manager = SaveManager(Path(tmp) / "game.json", clock=lambda: now[0])
            game.economy.get("metal").amount = 1000.0
            manager.save(game)
            now[0] = 1100.0
            first_payload = manager.load()
            first_report = manager.restore(game, first_payload)
            after_first = game.economy.get("metal").amount
            self.assertAlmostEqual(first_report["resources"]["metal"], 220.0, places=2)
            second_payload = manager.load()
            second_report = manager.restore(game, second_payload)
            self.assertAlmostEqual(second_report["elapsed_seconds"], 0.0)
            self.assertAlmostEqual(game.economy.get("metal").amount, after_first, places=6)

    def test_zero_baseline_production_survives_save_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = FakeGame(tmp)
            source.economy = ResourceManager(new_game=True)
            source.buildings = BuildingManager(source.economy)
            source.mining = MiningManager(source.economy, initial_ship_count=0)
            source.fleet = FleetManager(source.economy, source.buildings, source.mining)
            source.technology = TechnologyManager(
                source.economy, save_path=Path(tmp) / "source-tech.json"
            )
            source._applied_technology_bonuses = None
            source._apply_technology_bonuses()
            manager = SaveManager(Path(tmp) / "fresh.json", clock=lambda: 1000.0)
            manager.save(source)

            target = FakeGame(tmp)
            payload = manager.load()
            manager.restore(target, payload, apply_offline=False)
            for resource in target.economy.resources.values():
                self.assertEqual(resource.amount, 0.0)
                self.assertEqual(resource.production, 0.0)
                self.assertEqual(resource.consumption, 0.0)

    def test_both_corrupt_files_do_not_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SaveManager(Path(tmp) / "save.json")
            manager.path.write_text("not json", encoding="utf-8")
            manager.backup_path.write_text("{also broken", encoding="utf-8")
            self.assertIsNone(manager.load())
            self.assertEqual(len(manager.warnings), 2)

    def test_offline_progress_is_capped_at_eight_hours(self):
        resources = SimpleNamespace(resources={
            "energy": FakeResource(100000, 2, 1),
            "metal": FakeResource(0, 3, 1),
        })
        economy = SimpleNamespace(resources=resources.resources,
                                  get=lambda key: resources.resources[key])
        tech, buildings, mining, fleet = (FakeManager() for _ in range(4))
        game = SimpleNamespace(economy=economy, technology=tech, buildings=buildings,
                               mining=mining, fleet=fleet,
                               _apply_technology_bonuses=lambda: None)
        manager = SaveManager()
        report = manager.simulate_offline(game, MAX_OFFLINE_SECONDS + 500)
        self.assertEqual(report["elapsed_seconds"], MAX_OFFLINE_SECONDS)
        self.assertTrue(report["capped"])
        self.assertAlmostEqual(resources.resources["metal"].amount, 2 * MAX_OFFLINE_SECONDS)
        self.assertAlmostEqual(tech.elapsed, MAX_OFFLINE_SECONDS)

    def test_offline_progress_respects_storage_capacity(self):
        resources = SimpleNamespace(resources={
            "energy": FakeResource(100, 1, 0),
            "metal": FakeResource(9, 10, 0, capacity=10),
        })
        economy = SimpleNamespace(resources=resources.resources,
                                  get=lambda key: resources.resources[key])
        tech, buildings, mining, fleet = (FakeManager() for _ in range(4))
        game = SimpleNamespace(economy=economy, technology=tech, buildings=buildings,
                               mining=mining, fleet=fleet,
                               _apply_technology_bonuses=lambda: None)
        report = SaveManager().simulate_offline(game, 10)
        self.assertEqual(resources.resources["metal"].amount, 10)
        self.assertEqual(report["resources"]["metal"], 1)



    def test_new_game_archives_existing_saves_without_deleting_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            primary = base / "save.json"
            backup = base / "save.json.bak"
            primary.write_text("primary", encoding="utf-8")
            backup.write_text("backup", encoding="utf-8")
            archived = archive_existing_files((primary, backup), base / "archive", timestamp="test")
            self.assertEqual(len(archived), 2)
            self.assertTrue(primary.exists())
            self.assertTrue(backup.exists())
            self.assertEqual((base / "archive" / "test_save.json").read_text(), "primary")
            self.assertEqual((base / "archive" / "test_save.json.bak").read_text(), "backup")

if __name__ == "__main__":
    unittest.main()
