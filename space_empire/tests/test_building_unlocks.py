import unittest
from types import SimpleNamespace

from progression.building_unlocks import allowed_building_ids


BALANCE = {
    "available_buildings_by_stage": {
        "awakening": ["core"],
        "power": ["solar_array"],
        "mining": ["solar_array", "smelter", "warehouse"],
    }
}
AVAILABLE = {"solar_array", "smelter", "warehouse"}


class BuildingUnlockResolutionTests(unittest.TestCase):
    def test_power_stage_exposes_solar_array(self):
        p = SimpleNamespace(balance=BALANCE, stage_id="power",
                             active_task_id="awakening", stage_index=1,
                             stages=[{"id": "awakening"}, {"id": "power"}])
        self.assertEqual(allowed_building_ids(p, AVAILABLE), {"solar_array"})

    def test_stale_stage_id_uses_active_task_and_stage_index(self):
        p = SimpleNamespace(balance=BALANCE, stage_id="awakening",
                             active_task_id="power", stage_index=1,
                             stages=[{"id": "awakening"}, {"id": "power"}])
        self.assertEqual(allowed_building_ids(p, AVAILABLE), {"solar_array"})

    def test_unknown_stage_uses_valid_stage_index(self):
        p = SimpleNamespace(balance=BALANCE, stage_id="broken_stage",
                             active_task_id="broken_stage", stage_index=1,
                             stages=[{"id": "awakening"}, {"id": "power"}])
        self.assertEqual(allowed_building_ids(p, AVAILABLE), {"solar_array"})

    def test_completed_campaign_allows_all_buildings(self):
        p = SimpleNamespace(balance=BALANCE, stage_id="empire_established",
                             active_task_id=None, stage_index=3, stages=[])
        self.assertEqual(allowed_building_ids(p, AVAILABLE), AVAILABLE)

    def test_unknown_state_does_not_unlock_future_buildings(self):
        p = SimpleNamespace(balance=BALANCE, stage_id="broken_stage",
                             active_task_id="broken_stage", stage_index=99, stages=[])
        self.assertEqual(allowed_building_ids(p, AVAILABLE), set())

    def test_missing_balance_does_not_hide_constructor(self):
        p = SimpleNamespace(balance={}, stage_id="power")
        self.assertEqual(allowed_building_ids(p, AVAILABLE), AVAILABLE)


if __name__ == "__main__":
    unittest.main()
