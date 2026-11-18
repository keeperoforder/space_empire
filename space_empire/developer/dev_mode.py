"""Developer-only controls and conservative campaign diagnostics."""
from __future__ import annotations
import json
from pathlib import Path
import pygame


SPEEDS = (1, 2, 5, 10, 50, 100)


class DeveloperMode:
    def __init__(self, game):
        self.game = game
        self.visible = True
        self.paused = False
        self.speed_index = 0
        self.status = "Developer Mode active"
        self.messages = []
        self.scroll = 0
        self.buttons = {}
        self.selected_resource = "metal"
        self.selected_building = "solar_array"
        self.selected_mission_index = 0
        self.amount_entry = False
        self.amount_buffer = ""
        self.manual_mutations = False
        self.automated_tester = None

    @property
    def speed(self):
        return SPEEDS[self.speed_index]

    def log(self, message):
        self.status = str(message)
        self.messages.append(str(message))
        self.messages = self.messages[-8:]

    def adjust_resource(self, key, amount):
        resource = self.game.economy.get(key)
        resource.amount = max(0.0, min(resource.capacity, resource.amount + float(amount)))
        self.log(f"{key}: {resource.amount:.1f}")

    def set_resource(self, key, amount):
        resource = self.game.economy.get(key)
        resource.amount = max(0.0, min(resource.capacity, float(amount)))
        self.log(f"{key} set to {resource.amount:.1f}")

    def instant_build(self):
        for project in self.game.buildings.constructions:
            project.elapsed = project.duration
        self.game.buildings.update(0)
        self.game._sync_completed_buildings()
        self.log("Construction queue completed")

    def speed_production(self, factor=10):
        for resource in self.game.economy.resources.values():
            if resource.production > 0:
                resource.amount = min(resource.capacity,
                                      resource.amount + resource.production * float(factor))
        self.log(f"Production boosted for {factor} seconds (one-time)")

    def complete_research(self):
        active = self.game.technology.active_research
        if not active:
            self.log("No active research")
            return
        tech_id = active["technology_id"]
        self.game.technology.update(10**9)
        self.game._apply_technology_bonuses()
        self.log(f"Research completed: {tech_id}")

    def unlock_all_technologies(self):
        tm = self.game.technology
        tm.active_research = None
        for item in tm.technologies.values():
            item["state"] = "completed"
        tm._refresh_states()
        tm._recalculate_bonuses()
        tm.save()
        self.game._applied_technology_bonuses = None
        self.game._apply_technology_bonuses()
        self.log("All technologies unlocked")

    def remove_resource(self, key, amount):
        self.adjust_resource(key, -abs(float(amount)))

    def unlock_all_chapters(self):
        self.game.campaign_manager.developer_unlock_all = True
        for mission in self.game.campaign_manager.missions.values():
            if mission["status"] != "completed":
                mission["status"] = "available"
        self.log("All campaign chapters and missions unlocked for this test session")

    def instant_upgrade(self, building_id):
        ok, message = self.game.buildings.start_upgrade(building_id)
        if ok:
            for project in self.game.buildings.constructions:
                if project.building_id == building_id and getattr(project, "is_upgrade", False):
                    project.elapsed = project.duration
            self.game.buildings.update(0)
            self.game._sync_completed_buildings()
        self.log(message)
        return ok, message

    def unlock_all_buildings(self):
        # This changes only the in-memory test catalog, never the JSON balance data.
        for item in self.game.buildings.catalog.values():
            item["buildable"] = True
        self.game.progression.refresh_section_access(self.game)
        self.log("All building definitions enabled for this test session")

    def build_instant(self, building_id):
        self.unlock_all_buildings()
        ok, message = self.game.buildings.start_build(building_id)
        if ok:
            self.instant_build()
        self.log(message)
        return ok, message

    def unlock_all_ships(self):
        self.unlock_all_buildings()
        if self.game.buildings.count("hangar") == 0:
            self.game.buildings.owned.setdefault("hangar", []).append(
                {"level": 1, "instance_id": "dev-hangar-001"})
            self.game.buildings._recalculate_effects()
            definition = self.game.buildings.definition("hangar")
            self.game.station.add_constructed_building(
                "hangar", definition["name"], definition["sprite"])
        self.log("Ship production unlocked through a developer-only hangar")

    def select_mission(self, mission_id):
        cm = self.game.campaign_manager
        cm.developer_unlock_all = False
        if mission_id not in cm.missions:
            self.log(f"Unknown mission: {mission_id}")
            return False
        ordered = [mid for chapter in cm.chapters for mid in chapter["missions"]]
        target_index = ordered.index(mission_id)
        # Developer selection deliberately bypasses earlier objectives, but does
        # not issue their rewards or alter the normal campaign JSON.
        for index, mid in enumerate(ordered):
            if index < target_index:
                cm.missions[mid]["status"] = "completed"
            elif index == target_index:
                cm.missions[mid]["status"] = "available"
            else:
                cm.missions[mid]["status"] = "locked"
        target = cm.missions[mission_id]
        self.log(f"Selected mission: {target['title']}")
        return True

    def complete_current_mission(self):
        cm = self.game.campaign_manager
        current = next((m for m in cm.missions.values() if m["status"] == "available"), None)
        if not current:
            self.log("No available mission")
            return False
        current["progress"] = current["objective"].get("amount", 1)
        current["status"] = "completed"
        for key, value in current.get("rewards", {}).items():
            self.game.economy.add(key, value)
        cm._recalculate()
        self.log(f"Force-completed mission: {current['title']} (rewards granted once)")
        return True

    def skip_to_next_mission(self):
        cm = self.game.campaign_manager
        rows = list(cm.missions.values())
        current = next((i for i,m in enumerate(rows) if m["status"] == "available"), -1)
        if current < 0:
            self.log("No current mission")
            return False
        rows[current]["status"] = "completed"
        for key,value in rows[current].get("rewards",{}).items():
            self.game.economy.add(key,value)
        cm._recalculate()
        self.log("Advanced one mission; its configured reward was granted")
        return True

    def select_next_mission(self):
        ids = list(self.game.campaign_manager.missions)
        if not ids:
            return False
        self.selected_mission_index = (self.selected_mission_index + 1) % len(ids)
        return self.select_mission(ids[self.selected_mission_index])

    def reset_missions(self):
        cm = self.game.campaign_manager
        cm.developer_unlock_all = False
        for m in cm.missions.values():
            m["status"], m["progress"] = "locked", 0
        first = cm.chapters[0]["missions"][0]
        cm.missions[first]["status"] = "available"
        cm.flags.clear()
        self.log("Campaign mission state reset (test save only)")

    def mission_diagnostics(self):
        cm = self.game.campaign_manager
        rows = []
        for chapter in cm.chapters:
            for mid in chapter["missions"]:
                m = cm.missions[mid]
                obj = m["objective"]
                missing = []
                if obj["type"] == "resource":
                    r = self.game.economy.get(obj["key"])
                    if r.amount < obj["amount"]:
                        missing.append(f"{obj['key']}: {obj['amount']-r.amount:.1f}")
                elif obj["type"] == "building":
                    have = self.game.buildings.count(obj["key"])
                    if have < obj["amount"]:
                        missing.append(f"{obj['key']}: {obj['amount']-have} more")
                elif obj["type"] == "ship":
                    have = sum(s.ship_type == obj["key"] for s in self.game.fleet.ships)
                    if have < obj["amount"]:
                        missing.append(f"{obj['key']}: {obj['amount']-have} more")
                elif obj["type"] == "mined":
                    have = self.game.mining.delivered_total
                    if have < obj["amount"]:
                        missing.append(f"mined: {obj['amount']-have:.1f}")
                rows.append((chapter["title"], m["title"], m["status"], missing))
        return rows

    def automated_campaign_audit(self):
        """Conservative static feasibility pass; never grants resources or completes missions."""
        cm = self.game.campaign_manager
        report = ["SPACE EMPIRE — CAMPAIGN TEST REPORT",
                  "Mode: conservative diagnostics; no resource injection",
                  f"Chapters: {len(cm.chapters)} | Missions: {len(cm.missions)}", ""]
        blockers = 0
        for chapter in cm.chapters:
            report.append(f"[{chapter['title']}]")
            for mid in chapter["missions"]:
                m = cm.missions[mid]
                obj = m["objective"]
                notes = []
                if obj["type"] == "resource":
                    r = self.game.economy.get(obj["key"])
                    notes.append(f"target {obj['amount']} {obj['key']}; current {r.amount:.1f}; production {r.production:.2f}/s")
                elif obj["type"] == "building":
                    try:
                        d = self.game.buildings.definition(obj["key"])
                        notes.append(f"building {d['name']}; cost {d.get('cost',{})}; buildable={d.get('buildable')}")
                        for key, value in d.get("cost",{}).items():
                            r = self.game.economy.get(key)
                            if r.amount < value:
                                notes.append(f"current deficit {key}={value-r.amount:.1f}")
                    except KeyError:
                        notes.append("ERROR: building definition missing")
                elif obj["type"] == "ship":
                    notes.append(f"ship type {obj['key']}; requires hangar={self.game.buildings.count('hangar')>0}")
                elif obj["type"] == "mined":
                    notes.append(f"mining target {obj['amount']}; mining ships={len(self.game.mining.ships)}")
                elif obj["type"] == "tech_count":
                    notes.append(f"completed technologies required={obj['amount']}")
                elif obj["type"] == "tech_keyword":
                    notes.append(f"technology keyword alternatives={obj['keys']}")
                else:
                    notes.append(f"objective type {obj['type']} needs runtime verification")
                status = m["status"]
                if any(x.startswith("ERROR") for x in notes):
                    blockers += 1
                report.append(f"- {m['id']} | {status} | {m['title']}: " + "; ".join(notes))
            report.append("")
        report += [f"Static errors: {blockers}",
                   "NOTE: This report does not claim full campaign completion. Resource flow, mission transitions and runtime objectives require a deterministic full simulation."]
        out = Path(self.game.dev_save_dir) / "campaign_test_report.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(report), encoding="utf-8")
        self.log(f"Campaign diagnostics written: {out.name}")
        return out

    def start_automated_test(self):
        # Reinitialize this Game object, not the application process, with a new
        # run-scoped save and a fresh progression/economy state.
        game = self.game
        audio = getattr(game, "audio_manager", None)
        from game import Game
        Game.__init__(game, load_saved=False, developer_mode=True, automated_test=True)
        game.audio_manager = audio
        from developer.automated_tester import AutomatedCampaignTester
        game.dev_tools.automated_tester = AutomatedCampaignTester(game)
        ok, message = game.dev_tools.automated_tester.start()
        game.dev_tools.log(message)
        return ok

    def update_automated_test(self, dt):
        if self.automated_tester:
            self.automated_tester.update(dt)

    def handle_event(self, event):
        tester_active = bool(self.automated_tester and self.automated_tester.state in ("RUNNING", "PAUSED"))
        if tester_active and event.type == pygame.KEYDOWN and event.key in (
                pygame.K_F2, pygame.K_F3, pygame.K_F4, pygame.K_F7):
            self.log("Manual resource cheats are disabled during automated testing.")
            return True
        if event.type == pygame.KEYDOWN and self.amount_entry:
            if event.key == pygame.K_RETURN:
                try:
                    self.set_resource(self.selected_resource, float(self.amount_buffer or "0"))
                except ValueError:
                    self.log("Invalid resource amount")
                self.amount_entry = False
                self.amount_buffer = ""
            elif event.key == pygame.K_BACKSPACE:
                self.amount_buffer = self.amount_buffer[:-1]
            elif event.unicode and (event.unicode.isdigit() or event.unicode in ".,"):
                self.amount_buffer += event.unicode.replace(",", ".")
            return True
        if tester_active and event.type == pygame.KEYDOWN and event.key in (
                pygame.K_F2, pygame.K_F3, pygame.K_F4, pygame.K_F7):
            self.log("Manual resource cheats are disabled during automated testing.")
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
            self.amount_entry = True
            self.amount_buffer = ""
            self.log(f"Enter exact amount for {self.selected_resource}")
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F12:
            self.visible = not self.visible
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F10:
            self.paused = not self.paused
            self.log("Paused" if self.paused else "Resumed")
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
            self.speed_index = (self.speed_index + 1) % len(SPEEDS)
            self.log(f"Game speed: {self.speed}x")
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
            keys=list(self.game.economy.resources)
            self.selected_resource=keys[(keys.index(self.selected_resource)+1)%len(keys)] if self.selected_resource in keys else keys[0]
            self.log(f"Selected resource: {self.selected_resource}")
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F7:
            self.set_resource(self.selected_resource, 1000)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
            self.adjust_resource(self.selected_resource, 100)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
            self.remove_resource(self.selected_resource, 100)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F6:
            keys=list(self.game.buildings.catalog)
            self.selected_building=keys[(keys.index(self.selected_building)+1)%len(keys)] if self.selected_building in keys else keys[0]
            self.log(f"Selected building: {self.selected_building}")
            return True
        if not self.visible or event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        for key, rect in self.buttons.items():
            if rect.collidepoint(event.pos):
                actions = {
                    "play_test": self.start_automated_test,
                    "pause": lambda: (self.automated_tester.pause() if self.automated_tester else None, setattr(self, "paused", True)),
                    "resume": lambda: (self.automated_tester.resume() if self.automated_tester else None, setattr(self, "paused", False)),
                    "stop_test": lambda: self.automated_tester.stop() if self.automated_tester else None,
                    "restart_test": self.start_automated_test,
                    "export_error": lambda: self.automated_tester.export_error_report() if self.automated_tester else self.automated_campaign_audit(),
                    "export_full": lambda: self.automated_tester.export_full_report() if self.automated_tester else self.automated_campaign_audit(),
                    "pause": lambda: setattr(self, "paused", True),
                    "resume": lambda: setattr(self, "paused", False),
                    "speed": lambda: setattr(self, "speed_index", (self.speed_index+1)%len(SPEEDS)),
                    "instant_build": self.instant_build,
                    "research": self.complete_research,
                    "techs": self.unlock_all_technologies,
                    "buildings": self.unlock_all_buildings,
                    "ships": self.unlock_all_ships,
                    "complete": self.complete_current_mission,
                    "skip": self.skip_to_next_mission,
                    "reset": self.reset_missions,
                    "audit": self.automated_campaign_audit,
                    "metal": lambda: self.adjust_resource("metal", 100),
                    "remove_metal": lambda: self.remove_resource("metal", 100),
                    "remove_energy": lambda: self.remove_resource("energy", 100),
                    "chapters": self.unlock_all_chapters,
                    "build_selected": lambda: self.build_instant(self.selected_building),
                    "upgrade_selected": lambda: self.instant_upgrade(self.selected_building),
                    "mission_next": self.select_next_mission,
                    "energy": lambda: self.adjust_resource("energy", 100),
                    "fuel": lambda: self.adjust_resource("fuel", 50),
                    "crystals": lambda: self.adjust_resource("crystals", 50),
                    "credits": lambda: self.adjust_resource("credits", 500),
                    "science": lambda: self.adjust_resource("science", 50),
                }
                manual_actions = {
                    "metal", "energy", "fuel", "crystals", "credits", "science",
                    "remove_metal", "remove_energy", "instant_build", "research",
                    "techs", "buildings", "ships", "complete", "skip", "reset",
                    "chapters", "build_selected", "upgrade_selected", "mission_next",
                }
                if tester_active and key in manual_actions:
                    self.log("Manual developer cheats are disabled during automated testing.")
                    return True
                actions[key]()
                return True
        return False

    def draw(self, surface):
        if not self.visible:
            return
        w,h=surface.get_size()
        panel=pygame.Rect(w-440,78,425,h-88)
        shade=pygame.Surface(panel.size,pygame.SRCALPHA); shade.fill((5,13,27,238))
        surface.blit(shade,panel.topleft)
        pygame.draw.rect(surface,(61,174,215),panel,2,border_radius=10)
        title=pygame.font.SysFont("segoeui",21,True)
        body=pygame.font.SysFont("segoeui",14)
        small=pygame.font.SysFont("segoeui",12)
        def txt(value,x,y,font=body,color=(205,224,239)):
            surface.blit(font.render(str(value)[:54],True,color),(x,y))
        x,y=panel.x+14,panel.y+12
        txt("DEVELOPER / TEST MODE",x,y,title,(100,220,255)); y+=30
        cm=self.game.campaign_manager
        current=next((m for m in cm.missions.values() if m["status"]=="available"),None)
        chapter=cm.current_chapter()
        txt(f"Chapter: {chapter['title'] if chapter else '—'}",x,y); y+=20
        txt(f"Mission: {current['title'] if current else 'Campaign complete'}",x,y); y+=20
        if current:
            obj=current["objective"]
            txt(f"Requirement: {obj['type']} {obj.get('key','')} {obj.get('amount',1)}",x,y,small,(255,205,115)); y+=17
        txt(f"Speed: {self.speed}x | {'PAUSED' if self.paused else 'RUNNING'}",x,y,(body),(255,205,115)); y+=24
        txt("RESOURCES",x,y,title,(100,220,255)); y+=24
        for key,r in list(self.game.economy.resources.items())[:6]:
            txt(f"{key}: {r.amount:.1f} / {r.capacity:.0f}",x,y,small); y+=16
        y+=5
        txt("ACTIONS",x,y,title,(100,220,255)); y+=28
        self.buttons={}
        self.buttons["play_test"] = pygame.Rect(x, y, panel.width-28, 30)
        play_rect = self.buttons["play_test"]
        pygame.draw.rect(surface, (12, 76, 96), play_rect, border_radius=6)
        pygame.draw.rect(surface, (78, 220, 244), play_rect, 2, border_radius=6)
        play_label = small.render("▶ PLAY — START AUTOMATED TEST", True, (235, 251, 255))
        surface.blit(play_label, play_label.get_rect(center=play_rect.center))
        y += 36
        specs=[("pause","PAUSE"),("resume","RESUME"),("stop_test","STOP TEST"),("restart_test","RESTART TEST"),("export_error","EXPORT ERROR REPORT"),("export_full","EXPORT FULL TEST REPORT"),("metal","+100 metal"),("energy","+100 energy"),("fuel","+50 fuel"),
               ("crystals","+50 crystals"),("credits","+500 credits"),("science","+50 science"),
               ("instant_build","Finish construction"),("research","Finish research"),
               ("techs","Unlock all technologies"),("buildings","Unlock all buildings"),
               ("ships","Enable ship testing"),("complete","Complete mission"),
               ("skip","Next mission"),("reset","Reset missions"),("audit","Run campaign audit"),
               ("speed",f"Speed: {self.speed}x")]
        bw=(panel.width-36)//2
        for i,(key,label) in enumerate(specs):
            col=i%2; row=i//2
            rect=pygame.Rect(x+col*(bw+8),y+row*29,bw,25)
            self.buttons[key]=rect
            pygame.draw.rect(surface,(13,47,68),(rect),border_radius=5)
            pygame.draw.rect(surface,(49,131,164),rect,1,border_radius=5)
            surface.blit(small.render(label,True,(218,237,248)),(rect.x+6,rect.y+5))
        y+=((len(specs)+1)//2)*29+6
        txt("F8 select resource | F2 set exact | F3 +100 | F4 -100 | F6 building",x,y,small,(125,195,225))
        if self.amount_entry:
            y += 16
            txt(f"Set {self.selected_resource}: {self.amount_buffer}_  [ENTER]",x,y,small,(255,215,130))
        y += 16
        if self.automated_tester:
            tester=self.automated_tester
            chapter=tester._chapter_for(tester.current_mission_id) if tester.current_mission_id else None
            txt(f"AUTO: {tester.state} | {len(tester.results)}/{len(self.game.campaign_manager.missions)} missions",x,y,small,(100,225,180)); y+=15
            txt(f"Chapter: {chapter['title'] if chapter else '—'} | Mission: {tester.current_mission_id or '—'}",x,y,small); y+=15
            txt("Step: "+tester.current_step,x,y,small,(255,205,120)); y+=15
            txt(f"Completed: {len(tester.results)} | Errors: {len(tester.errors)} | Failed ops: {len(tester.failed_operations)}",x,y,small); y+=15
            if tester.errors:
                latest=tester.errors[-1]
                txt(f"ERROR {latest['error_id']}: {latest['reason']}",x,y,small,(255,120,120)); y+=15
                txt(f"Required: {latest.get('required')} | Available: {latest.get('available')}",x,y,small,(255,180,140)); y+=15
        txt("STATUS: "+self.status,x,y,small,(255,202,125))
        for msg in self.messages[-3:]:
            y+=15; txt(msg,x,y,small,(151,190,213))
