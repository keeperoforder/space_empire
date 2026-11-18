import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GraphicsDetailUpgradeTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_planets_use_cached_textured_sprites_and_surface_features(self):
        source = self.read("graphics/celestial.py")
        for token in ("_sprite_cache", "random.Random", "pygame.draw.arc",
                      "pygame.draw.ellipse", "Atmospheric", "smoothscale"):
            self.assertIn(token, source)

    def test_asteroids_have_irregular_cached_surface_and_craters(self):
        source = self.read("graphics/mining_visuals.py")
        for token in ("asteroid_surfaces", "pygame.draw.polygon",
                      "pygame.draw.arc", "Mineral seams"):
            self.assertIn(token, source)

    def test_fleet_uses_detailed_png_hulls_and_animated_engine_effects(self):
        source = self.read("graphics/fleet_visuals.py")
        library = self.read("graphics/asset_library.py")
        for token in ("scaled_sprite", "ships", "engine_radius", "engine plume"):
            self.assertIn(token, source)
        self.assertIn("_SCALE_CACHE", library)
        for ship in ("scout", "miner", "transport", "frigate",
                     "battleship", "colonizer", "industrial"):
            self.assertTrue((ROOT / "assets" / "sprites" / "ships" /
                             f"{ship}.png").is_file())

    def test_nebula_clouds_are_pre_rendered_with_wisps_and_dust_knots(self):
        source = self.read("graphics/nebula.py")
        self.assertIn("Dusty star knots", source)
        self.assertIn("Multi-lobed gas volumes", source)
        self.assertIn("_scaled_cache", source)

    def test_major_png_asset_library_is_complete_and_transparent(self):
        from PIL import Image
        required = {
            "station": ("core.png", "solar_panel.png", "docking_bay.png",
                        "antenna.png", "engine.png", "radiator.png"),
            "buildings": ("solar.png", "smelter.png", "crystal.png", "fuel.png",
                          "hangar.png", "lab.png", "warehouse.png", "habitat.png",
                          "defense.png"),
            "planets": ("temperate.png", "desert.png", "ice.png", "lava.png", "moon.png"),
            "space": tuple(f"asteroid_{i}.png" for i in range(6)),
            "effects": tuple(f"construction_{i:02d}.png" for i in range(8)),
        }
        for folder, names in required.items():
            for name in names:
                path = ROOT / "assets" / "sprites" / folder / name
                self.assertTrue(path.is_file(), str(path))
                with Image.open(path) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertGreater(image.width, 64)
                    self.assertGreater(image.height, 64)
        technology_ids = (
            "energy_01", "energy_02", "energy_03", "mining_01", "mining_02",
            "mining_03", "engineering_01", "engineering_02", "engineering_03",
            "spaceflight_01", "spaceflight_02", "spaceflight_03",
            "colonization_01", "colonization_02", "colonization_03",
            "military_01", "military_02", "military_03", "ai_01", "ai_02", "ai_03"
        )
        for tech_id in technology_ids:
            self.assertTrue((ROOT / "assets" / "sprites" / "icons" /
                             f"{tech_id}.png").is_file())

    def test_station_sprite_factory_and_station_runtime_api_are_preserved(self):
        sprites = self.read("graphics/station_sprites.py")
        station = self.read("graphics/station.py")
        for token in ("make_core", "make_truss", "make_antenna",
                      "make_solar_panel", "make_building_sprite"):
            self.assertIn(f"def {token}", sprites)
        for token in ("add_constructed_building", "upgrade_constructed_building",
                      "contains_screen_point", "def draw"):
            self.assertIn(token, station)


if __name__ == "__main__":
    unittest.main()
