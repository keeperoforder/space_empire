import tempfile
import unittest
from pathlib import Path

from economy import ResourceManager
from buildings import BuildingManager
from technology import TechnologyManager
from progression import GameProgression


class NewGameProgressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.economy = ResourceManager(new_game=True)
        self.buildings = BuildingManager(self.economy)
        self.technology = TechnologyManager(
            self.economy, save_path=Path(self.tmp.name) / "tech.json"
        )
        self.progression = GameProgression(
            self.economy, self.buildings, self.technology
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_game_is_zero_and_has_no_passive_rates(self):
        for resource in self.economy.resources.values():
            self.assertEqual(resource.amount, 0)
            self.assertEqual(resource.production, 0)
            self.assertEqual(resource.consumption, 0)
        self.assertEqual(self.progression.commander_level, 1)
        self.assertEqual(self.progression.commander_xp, 0)
        self.assertEqual(self.buildings.count("core"), 1)
        self.assertEqual(sum(len(v) for k, v in self.buildings.owned.items() if k != "core"), 0)
        self.assertFalse(self.progression.is_unlocked("research"))
        self.assertTrue(all(item["state"] == "locked" for item in self.technology.technologies.values()))

    def test_salvage_is_one_shot_and_unlocks_next_tutorial_task(self):
        ok, _ = self.progression.perform_salvage()
        self.assertTrue(ok)
        self.assertEqual(self.economy.get("metal").amount, 130)
        self.assertEqual(self.progression.active_task_id, "power")
        before = {k: r.amount for k, r in self.economy.resources.items()}
        ok, _ = self.progression.perform_salvage()
        self.assertFalse(ok)
        self.assertEqual(before, {k: r.amount for k, r in self.economy.resources.items()})

    def test_salvage_manifest_is_atomic_when_storage_is_insufficient(self):
        self.economy.get("metal").capacity = 50
        before = {key: item.amount for key, item in self.economy.resources.items()}
        ok, _ = self.progression.perform_salvage()
        self.assertFalse(ok)
        self.assertEqual(before, {key: item.amount for key, item in self.economy.resources.items()})
        self.assertFalse(self.progression.salvage_used)

    def test_salvage_manifest_funds_first_solar_array_without_passive_income(self):
        self.progression.perform_salvage()
        ok, message = self.buildings.start_build("solar_array")
        self.assertTrue(ok, message)
        self.buildings.update(10000)
        self.progression.update()
        self.assertEqual(self.progression.active_task_id, "mining")
        self.assertEqual(self.buildings.count("solar_array"), 1)
        self.assertGreater(self.economy.get("energy").production, 0)
        self.assertEqual(self.economy.get("metal").production, 0)

    def test_progression_snapshot_restores_claimed_salvage(self):
        self.progression.perform_salvage()
        state = self.progression.snapshot()
        other = GameProgression(self.economy, self.buildings, self.technology)
        other.restore(state)
        self.assertTrue(other.salvage_used)
        self.assertEqual(other.active_task_id, "power")
        self.assertFalse(other.is_unlocked("research"))


if __name__ == "__main__":
    unittest.main()
