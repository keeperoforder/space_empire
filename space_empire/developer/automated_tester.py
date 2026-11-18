"""Autonomous campaign test runner using live game APIs and isolated saves."""
from __future__ import annotations
import json
import traceback
import uuid
from datetime import datetime
from pathlib import Path


class AutomatedCampaignTester:
    def __init__(self, game):
        self.game = game
        self.state = "IDLE"
        self.test_id = "TEST-RUN-" + uuid.uuid4().hex[:8].upper()
        self.error_id = None
        self.current_step = "Not started"
        self.current_mission_id = None
        self.elapsed_without_progress = 0.0
        self._last_progress = None
        self.results, self.errors, self.failed_operations = [], [], []
        self.started_at = self.finished_at = None
        self._test_save_path = Path(game.save_manager.path)

    def _now(self):
        return datetime.now().astimezone().isoformat()

    def start(self):
        if self.state == "RUNNING":
            return False, "Automated test is already running."
        if getattr(self.game, "_developer_cheats_used", False):
            return False, "Manual developer changes detected; restart Developer Mode before testing."
        if self.game.progression.stage_index != 1 or self.game.progression.stage_id != "power":
            return False, "A clean campaign start is required."
        cm = self.game.campaign_manager
        first = next((m for m in cm.missions.values() if m["status"] == "available"), None)
        if not first or first["id"] != cm.chapters[0]["missions"][0]:
            return False, "Campaign is not at its first mission."
        self.test_id = "TEST-RUN-" + uuid.uuid4().hex[:8].upper()
        self.error_id = None
        self.results, self.errors, self.failed_operations = [], [], []
        self.started_at, self.finished_at = self._now(), None
        self.elapsed_without_progress, self._last_progress = 0.0, None
        self.current_step = "Starting isolated test save"
        self._test_save_path.parent.mkdir(parents=True, exist_ok=True)
        self.game.save_manager.path = self._test_save_path
        self.game.save_manager.backup_path = self._test_save_path.with_suffix(self._test_save_path.suffix + ".bak")
        self.game._save_timer = 0.0
        self.game.safe_save()
        self.state = "RUNNING"
        self.current_step = "Read first mission requirements"
        return True, "Automated campaign test started."

    def pause(self):
        if self.state == "RUNNING":
            self.state = "PAUSED"

    def resume(self):
        if self.state == "PAUSED":
            self.state = "RUNNING"

    def stop(self):
        if self.state in ("RUNNING", "PAUSED"):
            self.state = "STOPPED"
            if self.game.dev_tools:
                self.game.dev_tools.paused = False
            self.finished_at, self.current_step = self._now(), "Stopped by user"
            self._write_reports()

    def _mission(self):
        return next((m for m in self.game.campaign_manager.missions.values()
                     if m["status"] == "available"), None)

    def _chapter_for(self, mission_id):
        return next((c for c in self.game.campaign_manager.chapters
                     if mission_id in c["missions"]), None)

    def _resources(self):
        return {k: round(r.amount, 2) for k, r in self.game.economy.resources.items()}

    def _record(self, mission, detail):
        if not any(r["mission_id"] == mission["id"] for r in self.results):
            chapter = self._chapter_for(mission["id"])
            self.results.append({"mission_id": mission["id"], "mission": mission["title"],
                "chapter": chapter["title"] if chapter else "Unknown", "status": "SUCCESS",
                "objective": mission["objective"], "details": detail})

    def _fail(self, mission, status, reason, operation, required=None, exc=None):
        chapter = self._chapter_for(mission["id"])
        error_id = "TEST-" + uuid.uuid4().hex[:8].upper()
        resources = self._resources()
        key = mission.get("objective", {}).get("key")
        report = {"error_id": error_id, "mission_id": mission["id"], "mission": mission["title"],
            "chapter": chapter["title"] if chapter else "Unknown", "status": status,
            "reason": reason, "operation": operation, "required": required,
            "available": resources.get(key) if key else resources, "resources": resources,
            "location": "developer/automated_tester.py:AutomatedCampaignTester._execute",
            "traceback": traceback.format_exc() if exc else None}
        self.errors.append(report)
        self.failed_operations.append(report)
        self.error_id, self.state = error_id, status
        self.current_step, self.finished_at = reason, self._now()
        self._write_reports()

    def _start_build(self, key):
        manager = self.game.buildings
        if manager.count(key) or any(p.building_id == key and not getattr(p, "is_upgrade", False)
                                     for p in manager.constructions):
            return True, "already built or in construction"
        definition = manager.definition(key)
        if not definition.get("buildable"):
            return False, f"{key} is not buildable in the current catalogue"
        return manager.start_build(key)

    def _execute(self, mission):
        game, obj = self.game, mission["objective"]
        kind, key, target = obj["type"], obj.get("key"), obj.get("amount", 1)
        cm = game.campaign_manager
        if kind == "resource":
            resource = game.economy.get(key)
            if resource.amount >= target:
                return
            if key == "energy" and game.buildings.count("solar_array") == 0:
                ok, message = self._start_build("solar_array")
                self.current_step = "Build solar array via BuildingManager.start_build"
                if not ok and "Недостатньо ресурсів" not in message:
                    self._fail(mission, "BLOCKED", message, "buildings.start_build(solar_array)",
                               game.buildings.definition("solar_array").get("cost"))
            return
        if kind == "building":
            if game.buildings.count(key) >= target:
                return
            ok, message = self._start_build(key)
            self.current_step = f"Build {key} via BuildingManager.start_build"
            if not ok and "Недостатньо ресурсів" not in message and "already built" not in message:
                self._fail(mission, "BLOCKED", message, "buildings.start_build", game.buildings.definition(key).get("cost"))
            return
        if kind == "mined":
            if game.mining.delivered_total >= target:
                return
            if not game.mining.ships:
                ok, message = game.mining.build_ship()
                self.current_step = "Build mining ship via MiningManager.build_ship"
                if not ok and "Недостатньо ресурсів" not in message and self.elapsed_without_progress > 90:
                    self._fail(mission, "BLOCKED", message, "mining.build_ship", game.mining.SHIP_COST)
            return
        if kind in ("ship", "fleet"):
            ship_type = key if kind == "ship" else "scout"
            count = sum(s.ship_type == ship_type for s in game.fleet.ships)
            if (count if kind == "ship" else len(game.fleet.ships)) >= target:
                return
            if not game.buildings.count("hangar"):
                ok, message = self._start_build("hangar")
                self.current_step = "Build hangar via BuildingManager"
            elif not any(p.get("ship_type") == ship_type for p in game.fleet.constructions):
                ok, message = game.fleet.build_ship(ship_type)
                self.current_step = f"Build {ship_type} via FleetManager.build_ship"
            else:
                return
            if not ok and "Недостатньо ресурсів" not in message and self.elapsed_without_progress > 90:
                self._fail(mission, "BLOCKED", message, "fleet.build_ship")
            return
        if kind == "systems":
            if sum(bool(s.get("discovered")) for s in game.galaxy.systems.values()) >= target:
                return
            if game.galaxy.expeditions:
                self.current_step = "Wait for current expedition to return"
                return
            scouts = game.galaxy.available_scouts(game.fleet)
            if not scouts:
                proxy = {"id": mission["id"], "title": mission["title"],
                         "objective": {"type": "ship", "key": "scout", "amount": 1}}
                self._execute(proxy)
                return
            system = next((sid for sid, row in game.galaxy.systems.items()
                           if not row.get("discovered") and row.get("accessible")), None)
            if not system:
                self._fail(mission, "BLOCKED", "No undiscovered accessible star system.",
                           "galaxy.launch_expedition")
            else:
                ok, message = game.galaxy.launch_expedition(game.fleet, system, scouts[0].id)
                self.current_step = f"Launch expedition via GalaxyManager: {system}"
                if not ok and "палива" not in message.lower() and self.elapsed_without_progress > 90:
                    self._fail(mission, "BLOCKED", message, "galaxy.launch_expedition")
            return
        if kind in ("tech_keyword", "tech_count"):
            completed = sum(v.get("state") == "completed" for v in game.technology.technologies.values())
            if kind == "tech_count" and completed >= target:
                return
            keys = obj.get("keys", [])
            if kind == "tech_keyword" and any(v.get("state") == "completed" and
                    any(k in (tid + " " + str(v.get("name", ""))).lower() for k in keys)
                    for tid, v in game.technology.technologies.items()):
                return
            candidates = [tid for tid, item in game.technology.technologies.items()
                          if item.get("state") == "available" and
                          (kind != "tech_keyword" or any(k in (tid + " " + str(item.get("name", ""))).lower()
                                                          for k in keys))]
            if not game.technology.active_research and candidates:
                ok, message = game.technology.start_research(candidates[0])
                self.current_step = f"Start research via TechnologyManager: {candidates[0]}"
                if not ok and "науки" not in message.lower() and self.elapsed_without_progress > 90:
                    self._fail(mission, "BLOCKED", message, "technology.start_research")
            return
        if kind == "flag":
            if key in cm.flags:
                return
            if not cm.active_event:
                event = next((e for e in cm.event_definitions if any(
                    key in choice.get("flags", []) for choice in e.get("choices", []))), None)
                cm.trigger_event(event["id"] if event else None)
            event = cm.active_event
            if event:
                choice = next((c for c in event.get("choices", []) if key in c.get("flags", [])), None)
                if choice:
                    ok, message = cm.choose_event(choice["id"])
                    self.current_step = f"Resolve story event via CampaignManager: {event['id']}"
                    if not ok:
                        self._fail(mission, "BLOCKED", message, "campaign_manager.choose_event")
                elif self.elapsed_without_progress > 30:
                    self._fail(mission, "BLOCKED", "Event choice cannot satisfy objective flag.",
                               "campaign_manager.choose_event")
            return
        if kind == "colonies":
            if len(game.colony_manager.colonies) >= target:
                return
            game.colony_manager.refresh_discoveries()
            if game.colony_manager.missions:
                self.current_step = "Wait for colony ship to return"
                return
            ships = game.colony_manager.available_colonizers()
            if not ships:
                if not game.buildings.count("hangar"):
                    ok, message = self._start_build("hangar")
                elif not any(p.get("ship_type") == "colonizer" for p in game.fleet.constructions):
                    ok, message = game.fleet.build_ship("colonizer")
                else:
                    return
                self.current_step = "Prepare colonizer through FleetManager"
                if not ok and "Недостатньо ресурсів" not in message and self.elapsed_without_progress > 90:
                    self._fail(mission, "BLOCKED", message, "fleet.build_ship(colonizer)")
            else:
                planet = next(((pid, p) for pid, p in game.colony_manager.planets.items()
                               if p.get("discovered") and not p.get("colonized") and p.get("type") != "gas_giant"), None)
                if planet:
                    ok, message = game.colony_manager.colonize(planet[0], ships[0].id)
                    self.current_step = f"Colonize via ColonyManager: {planet[0]}"
                    if not ok and self.elapsed_without_progress > 90:
                        self._fail(mission, "BLOCKED", message, "colony_manager.colonize")
                elif self.elapsed_without_progress > 120:
                    self._fail(mission, "BLOCKED", "No discovered habitable planet is available.",
                               "colony_manager.colonize")
            return
        if kind == "colony_level":
            colony = next(iter(game.colony_manager.colonies.values()), None)
            if colony and colony.get("development", 1) >= target:
                return
            if colony:
                pid = colony["planet_id"]
                ok, message = (game.colony_manager.build_base(pid) if not colony.get("base_built")
                               else game.colony_manager.develop(pid))
                self.current_step = "Develop colony through ColonyManager"
                if not ok and "Недостатньо ресурсів" not in message and self.elapsed_without_progress > 90:
                    self._fail(mission, "BLOCKED", message, "colony_manager.develop")
            return
        self._fail(mission, "BLOCKED", f"Unsupported campaign objective: {kind}",
                   "campaign objective dispatcher")

    def _report_data(self):
        cm = self.game.campaign_manager
        missions = []
        recorded = {r["mission_id"] for r in self.results}
        for chapter in cm.chapters:
            for mid in chapter["missions"]:
                mission = cm.missions[mid]
                if mission["status"] == "completed" and mid in recorded:
                    status = "SUCCESS"
                elif mission["status"] == "completed" and cm._progress(mission["objective"]) < mission["objective"].get("amount", 1):
                    status = "SKIPPED"
                else:
                    status = "NOT TESTED"
                missions.append({"mission_id": mid, "chapter": chapter["title"],
                                 "mission": mission["title"], "status": status})
        completed = sum(m["status"] == "SUCCESS" for m in missions)
        return {"test_id": self.test_id, "run_id": getattr(self.game, "automated_test_run_id", None),
                "error_id": self.error_id, "state": self.state, "started_at": self.started_at,
                "finished_at": self.finished_at, "mission_id": self.current_mission_id,
                "current_step": self.current_step, "resources": self._resources(),
                "completed_missions": completed, "total_missions": len(missions),
                "failed_operations": self.failed_operations, "error_count": len(self.errors),
                "missions": missions, "errors": self.errors}

    def _resources(self):
        return {k: round(r.amount, 2) for k, r in self.game.economy.resources.items()}

    def _write_reports(self):
        data = self._report_data()
        out = Path(self.game.dev_save_dir) / "automated_test"
        out.mkdir(parents=True, exist_ok=True)
        (out / "TEST_REPORT.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = ["SPACE EMPIRE — AUTOMATED CAMPAIGN TEST", f"TEST ID: {data['test_id']}",
                 f"STATE: {data['state']}", f"PROGRESS: {data['completed_missions']}/{data['total_missions']}",
                 f"CURRENT STEP: {data['current_step']}", "", "MISSIONS"]
        lines.extend(f"{m['status']} | {m['chapter']} | {m['mission_id']} — {m['mission']}" for m in data["missions"])
        lines.extend(["", "ERRORS"])
        for error in self.errors:
            lines.extend([f"ERROR ID: {error['error_id']}", f"MISSION: {error['mission']}",
                          f"CHAPTER: {error['chapter']}", f"STATUS: {error['status']}",
                          f"REASON: {error['reason']}", f"OPERATION: {error['operation']}",
                          f"REQUIRED: {error.get('required')}", f"AVAILABLE: {error.get('available')}",
                          f"RESOURCES: {error.get('resources')}", f"LOCATION: {error.get('location')}",
                          "TRACEBACK:", error.get("traceback") or "No exception traceback.", "---"])
        (out / "TEST_REPORT.txt").write_text("\n".join(lines), encoding="utf-8")

    def _report_error_files(self):
        self._write_reports()
        data = self._report_data()
        out = Path(self.game.dev_save_dir) / "automated_test"
        payload = {"test_id": data["test_id"], "error_count": data["error_count"], "errors": data["errors"]}
        (out / "TEST_ERROR_REPORT.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "TEST_ERROR_REPORT.txt").write_text("\n".join(
            [f"ERROR ID: {e['error_id']} | MISSION: {e['mission']} | STATUS: {e['status']} | {e['reason']}\n{e.get('traceback') or ''}"
             for e in self.errors]), encoding="utf-8")

    def update(self, dt):
        if self.state != "RUNNING":
            return
        cm = self.game.campaign_manager
        try:
            cm._recalculate()
            mission = self._mission()
            if mission is None:
                if all(m["status"] == "completed" for m in cm.missions.values()):
                    self.state, self.current_step, self.finished_at = "COMPLETED", "All objectives completed by live game systems", self._now()
                else:
                    self._fail({"id": "campaign", "title": "Campaign", "objective": {}}, "BLOCKED",
                               "No active mission while campaign still contains locked missions.", "CampaignManager._recalculate")
                self._write_reports()
                return
            self.current_mission_id = mission["id"]
            progress = cm._progress(mission["objective"])
            if progress == self._last_progress:
                self.elapsed_without_progress += max(0.0, float(dt))
            else:
                self._last_progress, self.elapsed_without_progress = progress, 0.0
            self.current_step = f"Evaluate {mission['objective']['type']} objective ({progress}/{mission['objective'].get('amount', 1)})"
            self._execute(mission)
            cm._recalculate()
            if mission["status"] == "completed":
                self._record(mission, f"Live objective value reached {cm._progress(mission['objective'])}.")
                self.current_step = "SUCCESS — " + mission["title"]
                self.elapsed_without_progress, self._last_progress = 0.0, None
            elif self.elapsed_without_progress > 120 and self.state == "RUNNING":
                self._fail(mission, "BLOCKED", "No objective progress after 120 simulated seconds.",
                           self.current_step, mission["objective"])
            self.game.save_manager.save(self.game)
        except Exception as exc:
            mission = self._mission() or {"id": "unknown", "title": "Unknown mission", "objective": {}}
            self._fail(mission, "ERROR", f"{type(exc).__name__}: {exc}", self.current_step, exc=exc)

    def export_error_report(self):
        self._report_error_files()
        return Path(self.game.dev_save_dir) / "automated_test" / "TEST_ERROR_REPORT.txt"

    def export_full_report(self):
        self._write_reports()
        return Path(self.game.dev_save_dir) / "automated_test"

    def export_reports(self):
        return self.export_full_report()
