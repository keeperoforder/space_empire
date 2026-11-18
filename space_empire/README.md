# Space Empire

2D Sci-Fi idle/management strategy game built with Python and pygame-ce.

## Requirements
- Windows 10/11 64-bit (recommended for the supplied EXE build script)
- Python 3.10 or newer
- pygame-ce 2.5.3+
- Internet access only for installing Python dependencies; the game itself uses local assets/data.

## Install and run from source
1. Install Python 3.10+ and enable **Add Python to PATH**.
2. Open Command Prompt in the project folder.
3. Create an environment: `py -3 -m venv .venv`
4. Activate it: `.venv\\Scripts\\activate` (Windows) or `source .venv/bin/activate` (Linux/macOS).
5. Install dependencies: `python -m pip install -r requirements.txt`
6. Launch: `python main.py`

The launcher provides the splash screen, main menu, settings and loading screen. Use **Продовжити** to load the existing save or **Нова гра** to start without restoring it.

## Windows EXE build
1. On Windows, run `build_windows.bat`.
2. PyInstaller creates `dist\\SpaceEmpire\\SpaceEmpire.exe` and its supporting files.
3. Distribute the complete `dist\\SpaceEmpire` folder, not the EXE alone.
4. Test the build on a clean Windows account before publishing.

The build uses the `onedir` layout so JSON catalogs, audio and image assets remain accessible. In source runs, saves/settings are written under `saves/`. In a frozen Windows build, writable user data is stored under `%APPDATA%\\SpaceEmpire`.

## Controls
- Mouse: select station, navigate panels, operate management screens.
- Mouse wheel / +/-: zoom (when map/research screens are not active).
- F11 or Alt+Enter: toggle fullscreen.
- Ctrl+Q: exit gameplay.
- Window close button: exit.

## Settings
The launcher supports 1280×720, 1366×768, 1600×900 and 1920×1080, fullscreen, music, sound effects and volume. Settings are stored in `saves/settings.json`.

## Data and saves
- Campaign definitions: `campaign/campaign.json`
- Building catalog: `buildings/catalog.json`
- Technology tree: `technology/technology_tree.json`
- Galaxy: `galaxy/galaxy_catalog.json`
- Market: `automation/market.json`
- Saves: `saves/space_empire_save.json` and backup `.bak`

## Tests and audit
Run `python -m unittest discover -s tests -v` from the project root.
Run `python -m compileall -q .` for a syntax/bytecode compilation check.

## Release audit status
Automated domain tests cover economy, construction, mining, fleet, technology, save integrity/offline progress, galaxy exploration, colonies, automation/trading and campaign events. The release environment used for this audit did not have pygame-ce installed and could not access package indexes, so interactive GUI, real FPS, audio-device output, memory profiling and Windows EXE execution remain **not runtime-verified**. Do not treat this package as a signed/QA-certified Windows release until the manual test matrix has been completed on Windows.

## New-game opening progression

A fresh campaign starts with zero stockpiles and zero passive resource rates, commander
level 1 / 0 XP, only the command core, no mining ships or fleet vessels, no revealed
planetary objects, and all research locked. The opening station is rendered as damaged
wreckage around the command core.

The one-shot emergency salvage action is available in the opening briefing / Progress
panel. It consumes the nearby cargo wreck once and grants the explicit salvage manifest
defined in `progression/progression.json`. The next tutorial objective is to build the
first solar array. Resource production begins only when the corresponding building
finishes construction. Tutorial and commander state are stored in the main save.


## Ten-stage tutorial campaign

The opening progression is data-driven in `progression/campaign_progression.json`.
Each stage has a real manager-backed objective, unlocks only its relevant mechanics,
grants a one-time milestone reward, awards commander XP, and advances automatically.
The active quest and progression unlocks are included in the main save. The Progress
panel displays one active objective and supports replaying its explanation.


## Progression balance configuration

- `balance/progression_balance.json` contains the opening stock baseline, one-shot salvage manifest,
  stage milestone rewards, stage time targets, production rates, unlock prerequisites, and the
  per-stage building availability list.
- `balance/economy_costs.json` contains mining vessel, fleet ship, colony mission, colony base,
  and mining upgrade costs. The relevant managers load these values at startup.
- `progression/progression_graph.json` is the dependency graph; `progression/PROGRESSION_GRAPH.md`
  renders the graph in Mermaid.
- `progression/balance_audit.py` validates graph topology and simulates the mandatory resource
  spending path through the second colony to detect resource softlocks.
Run `python -m unittest tests.test_progression_balance -v` to validate the balance path.
