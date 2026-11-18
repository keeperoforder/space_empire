import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DeveloperModeIntegrationTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_launcher_has_separate_developer_entry(self):
        source = self.read("launcher.py")
        self.assertIn('("developer","Developer Mode / Тестування")', source)
        self.assertIn('developer_mode=(selected=="developer")', source)

    def test_developer_saves_are_isolated_from_normal_saves(self):
        source = self.read("game.py")
        self.assertIn('self.dev_save_dir / "developer_save.json" if developer_mode', source)
        self.assertIn('"technology_progress.json"', source)
        self.assertIn('not developer_mode', source)

    def test_developer_controls_cover_requested_systems(self):
        source = self.read("developer/dev_mode.py")
        for token in ("adjust_resource", "remove_resource", "set_resource",
                      "instant_build", "speed_production", "complete_research",
                      "unlock_all_technologies", "unlock_all_chapters",
                      "select_mission", "complete_current_mission",
                      "skip_to_next_mission", "reset_missions",
                      "mission_diagnostics", "automated_campaign_audit",
                      "instant_upgrade", "SPEEDS"):
            self.assertIn(token, source)

    def test_speed_steps_match_specification(self):
        source = self.read("developer/dev_mode.py")
        self.assertIn("SPEEDS = (1, 2, 5, 10, 50, 100)", source)

    def test_campaign_report_is_non_destructive_and_explicit(self):
        source = self.read("developer/dev_mode.py")
        self.assertIn("never grants resources or completes missions", source)
        self.assertIn("campaign_test_report.txt", source)
        self.assertIn("does not claim full campaign completion", source)

    def test_campaign_catalog_is_complete_and_ordered(self):
        data = json.loads((ROOT / "campaign/campaign.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["chapters"]), 8)
        self.assertEqual(len(data["missions"]), 16)
        ids = {m["id"] for m in data["missions"]}
        self.assertEqual(ids, {mid for c in data["chapters"] for mid in c["missions"]})

    def test_normal_save_manager_default_path_is_unchanged(self):
        source = self.read("game.py")
        self.assertIn('else "saves/space_empire_save.json"', source)


if __name__ == "__main__":
    unittest.main()
