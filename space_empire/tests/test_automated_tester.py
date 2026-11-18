import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from developer.automated_tester import AutomatedCampaignTester


class AutomatedTesterReportTests(unittest.TestCase):
    def make_tester(self, root):
        mission = {"id": "power", "title": "Restore power", "status": "available",
                   "progress": 0, "objective": {"type": "resource", "key": "energy", "amount": 100}}
        chapter = {"id": "awakening", "title": "Awakening", "missions": ["power"]}
        resources = {"energy": SimpleNamespace(amount=35.0, capacity=500.0, production=0.0,
                                                consumption=0.0, balance=0.0)}
        campaign = SimpleNamespace(chapters=[chapter], missions={"power": mission},
                                   _progress=lambda obj: resources[obj["key"]].amount)
        game = SimpleNamespace(dev_save_dir=Path(root), economy=SimpleNamespace(resources=resources),
                               campaign_manager=campaign, dev_tools=None)
        return AutomatedCampaignTester(game)

    def test_blocked_operation_has_unique_id_and_resource_context(self):
        with tempfile.TemporaryDirectory() as root:
            tester = self.make_tester(root)
            mission = tester.game.campaign_manager.missions["power"]
            tester._fail(mission, "BLOCKED", "No energy production", "wait_for_resource_production", 100)
            data = json.loads((Path(root) / "automated_test" / "TEST_REPORT.json").read_text(encoding="utf-8"))
            self.assertEqual(data["missions"][0]["status"], "NOT TESTED")
            self.assertEqual(data["errors"][0]["required"], 100)
            self.assertEqual(data["errors"][0]["available"], 35.0)
            self.assertTrue(data["errors"][0]["error_id"].startswith("TEST-"))

    def test_pause_resume_and_stop_write_a_report(self):
        with tempfile.TemporaryDirectory() as root:
            tester = self.make_tester(root)
            tester.state = "RUNNING"
            tester.pause()
            self.assertEqual(tester.state, "PAUSED")
            tester.resume()
            self.assertEqual(tester.state, "RUNNING")
            tester.stop()
            self.assertEqual(tester.state, "STOPPED")
            self.assertTrue((Path(root) / "automated_test" / "TEST_REPORT.json").exists())

    def test_force_completed_mission_is_skipped_not_success(self):
        with tempfile.TemporaryDirectory() as root:
            tester = self.make_tester(root)
            tester.game.campaign_manager.missions["power"]["status"] = "completed"
            data = tester._report_data()
            self.assertEqual(data["missions"][0]["status"], "SKIPPED")
            self.assertEqual(data["completed_missions"], 0)

    def test_outdated_crystal_extractor_mission_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            tester = self.make_tester(root)
            tester.game.campaign_manager.missions = {
                "mine": {"id": "mine", "objective": {"type": "building", "key": "crystal_extractor", "amount": 1}},
                "miner": {"id": "miner", "objective": {"type": "mined", "amount": 100}},
            }
            ok, message = tester._validate_campaign_contract()
            self.assertFalse(ok)
            self.assertIn("Outdated campaign data detected for mine", message)
    def test_test_id_is_separate_from_error_id(self):
        with tempfile.TemporaryDirectory() as root:
            tester = self.make_tester(root)
            test_id = tester.test_id
            tester._fail(tester.game.campaign_manager.missions["power"], "BLOCKED", "blocked", "operation", 100)
            data = tester._report_data()
            self.assertEqual(data["test_id"], test_id)
            self.assertNotEqual(data["test_id"], data["error_id"])


if __name__ == "__main__":
    unittest.main()
