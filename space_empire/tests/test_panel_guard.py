import unittest
from types import SimpleNamespace

from ui.panel_guard import PanelGuard


class PanelGuardTests(unittest.TestCase):
    def test_draw_exception_never_closes_panel_during_30_second_session(self):
        calls = []
        guard = PanelGuard(lambda component, exc: calls.append((component, str(exc))))
        panel = SimpleNamespace(visible=True)
        panel.draw = lambda surface: (_ for _ in ()).throw(RuntimeError("simulated draw failure"))
        for _ in range(30 * 60):
            guard.draw(panel, object(), "Будівництво")
            self.assertTrue(panel.visible)
        self.assertEqual(len(calls), 1)
        self.assertIn("simulated draw failure", guard.errors["Будівництво"])

    def test_event_exception_is_consumed_without_closing_or_resetting_panel(self):
        guard = PanelGuard()
        panel = SimpleNamespace(visible=True, selected_id="solar_array")
        panel.handle_event = lambda event: (_ for _ in ()).throw(ValueError("bad event"))
        self.assertTrue(guard.handle_event(panel, object(), "Будівництво"))
        self.assertTrue(panel.visible)
        self.assertEqual(panel.selected_id, "solar_array")

    def test_successful_draw_clears_previous_error(self):
        guard = PanelGuard()
        panel = SimpleNamespace(visible=True, draw=lambda surface: None)
        guard.errors["Будівництво"] = "old failure"
        self.assertTrue(guard.draw(panel, object(), "Будівництво"))
        self.assertNotIn("Будівництво", guard.errors)


if __name__ == "__main__":
    unittest.main()
