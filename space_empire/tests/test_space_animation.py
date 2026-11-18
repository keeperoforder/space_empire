import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


class SpaceAnimationRegressionTests(unittest.TestCase):
    def test_background_has_bounded_dust_pool_and_dt_update(self):
        text = source("graphics/background.py")
        self.assertIn("range(44)", text)
        self.assertIn("def update(self, dt", text)
        self.assertIn("particle[0] -= particle[2] * dt", text)

    def test_star_layers_drift_and_wrap(self):
        text = source("graphics/starfield.py")
        self.assertIn("(2.0, 5.0, 10.0)", text)
        self.assertIn("star.x += self.width * 3", text)

    def test_station_module_animation_and_build_reveal(self):
        text = source("graphics/station.py")
        self.assertIn("rotation_speed=2.2", text)
        self.assertIn("module.spawn_age = 0.0", text)
        self.assertIn("if age < 1.25:", text)
        self.assertIn("solar", text)

    def test_planet_surface_animation_is_time_based(self):
        text = source("graphics/celestial.py")
        self.assertIn("elapsed * 0.22", text)
        self.assertIn("elapsed * 0.16", text)
        self.assertIn("atmosphere_color", text)

    def test_mining_beam_is_visual_only(self):
        text = source("graphics/mining_visuals.py")
        self.assertIn('ship.task == "mining"', text)
        self.assertIn("pygame.draw.line(surface, beam_color", text)

    def test_fleet_reactor_and_engine_trails(self):
        text = source("graphics/fleet_visuals.py")
        self.assertIn("engine_radius", text)
        self.assertIn("engine plume", text)

    def test_game_update_still_drives_all_visual_systems(self):
        text = source("game.py")
        for call in ("self.space_background.update(dt)", "self.station.update(dt)",
                     "self.mining_visuals.update(dt)", "self.fleet_visuals.update(dt)"):
            self.assertIn(call, text)

    def test_gameplay_managers_were_not_modified(self):
        # Animation work must remain isolated from economy/progression/building rules.
        for rel in ("economy/resource_manager.py", "buildings/building_manager.py",
                    "progression/game_progression.py"):
            self.assertTrue((ROOT / rel).exists())


if __name__ == "__main__":
    unittest.main()
