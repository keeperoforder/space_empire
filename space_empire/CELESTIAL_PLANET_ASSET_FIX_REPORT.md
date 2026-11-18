# Celestial Planet Asset Initialization Fix

## Problem
`CelestialBody.draw()` requested a planet texture using `self._planet_asset`, but the attribute was never initialized. This caused startup to fail with `AttributeError` when a planet was drawn.

## Fix
Initialize `self._planet_asset` in `CelestialBody.__init__()` using the existing `_choose_planet_asset()` method before the sprite is drawn:

```python
self._planet_asset = self._choose_planet_asset()
```

## Validation
- `python -m compileall -q .` — passed.
- `python -m pytest -q` — 174 passed, 29 subtests passed.
- Pygame graphical runtime launch was not performed in this environment.
