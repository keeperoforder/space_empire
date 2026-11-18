"""Data-driven ten-stage tutorial, quest progression, unlocks and commander XP."""
from __future__ import annotations
import copy
import json
from pathlib import Path


class GameProgression:
    INTRO_MESSAGE = (
        "Командире, зв'язок із центральною мережею втрачено. Основні системи "
        "станції відключені. Виявлено залишки вантажного корабля поблизу. "
        "Для відновлення станції необхідно зібрати доступні матеріали."
    )

    MECHANIC_LABELS = {
        "overview": "Огляд", "building": "Будівництво", "mining": "Видобуток",
        "research": "Дослідження", "fleet": "Флот", "galaxy": "Галактична карта",
        "colonies": "Планети", "automation": "Автоматизація",
        "trade": "Торгівля", "campaign": "Кампанія", "defense": "Оборона",
        "settings": "Налаштування"
    }

    def __init__(self, economy, buildings, technology, data_dir=None):
        self.economy, self.buildings, self.technology = economy, buildings, technology
        base = Path(data_dir) if data_dir else Path(__file__).resolve().parent
        self.config = json.loads((base / "progression.json").read_text(encoding="utf-8"))
        self.data = json.loads((base / "campaign_progression.json").read_text(encoding="utf-8"))
        balance_path = base.parent / "balance" / "progression_balance.json"
        self.balance = json.loads(balance_path.read_text(encoding="utf-8")) if balance_path.exists() else {}
        self.stages = copy.deepcopy(self.data["stages"])
        for stage in self.stages:
            configured_reward = self.balance.get("stage_rewards", {}).get(stage["id"])
            if configured_reward is not None:
                stage["reward"] = copy.deepcopy(configured_reward)
        self.stage_index = 0
        self.stage_id = self.stages[0]["id"]
        self.commander_level = 1
        self.commander_xp = 0
        self.active_task_id = self.stage_id
        self.completed_tasks = []
        self.claimed_rewards = []
        self.seen_story_events = []
        self.unlocks = {key: key in ("overview", "campaign", "settings") for key in self.MECHANIC_LABELS}
        self.events = []
        self.salvage_used = False
        self.intro_seen = False
        self.story_message = self.INTRO_MESSAGE
        self.explanation_history = []
        self._last_objective_progress = 0
        self.technology.set_research_enabled(False)
        self.unlock("overview")
        self.unlock("campaign")
        self.unlock("settings")

    SECTION_REQUIREMENTS = {
        "Будівництво": ("building", "Завершіть аварійний збір уламків."),
        "Видобуток": ("mining", "Відновіть живлення станції та дочекайтеся виявлення доступного астероїдного поля."),
        "Дослідження": ("research", "Побудуйте наукову лабораторію."),
        "Флот": ("fleet", "Відновіть ангар станції."),
        "Галактична карта": ("galaxy", "Побудуйте розвідувальний корабель та обладнайте його для далекої експедиції."),
        "Планети": ("colonies", "Успішно завершіть першу розвідувальну експедицію та відкрийте планету."),
        "Торгівля": ("trade", "Побудуйте транспортний корабель і відновіть транспортну інфраструктуру."),
        "Автоматизація": ("automation", "Завершіть технологію «Експертні системи» (AI-01)."),
        "Кампанія": ("campaign", ""),
        "Оборона": ("defense", "Дочекайтеся першої небезпечної космічної події."),
        "Налаштування": ("settings", ""),
        "Огляд": ("overview", ""),
        "Прогрес": ("progress", ""),
    }

    SECTION_COMPLETION = {
        "Будівництво": ("power", "station"),
        "Видобуток": ("mining",),
        "Дослідження": ("science",),
        "Флот": ("fleet",),
        "Планети": ("colonies",),
        "Галактична карта": ("galaxy",),
        "Торгівля": ("empire",),
        "Автоматизація": ("automation",),
    }

    def _activate_stage_mechanics(self, game):
        # Stage entry never grants a UI section by itself. Real manager state
        # is checked in refresh_section_access().
        if game is not None:
            self.refresh_section_access(game)

    def refresh_section_access(self, game):
        buildings = game.buildings
        has_ship = lambda kind: any(ship.ship_type == kind for ship in game.fleet.ships)
        discovered_systems = sum(bool(item.get("discovered")) for item in game.galaxy.systems.values())
        requirements = {
            "building": self.stage_index >= 1,
            "mining": self.stage_index >= 2 and bool(game.mining.asteroids),
            "research": buildings.count("laboratory") >= 1,
            "fleet": buildings.count("hangar") >= 1,
            "galaxy": has_ship("scout") and self.stage_index >= 5,
            "colonies": discovered_systems >= 2 and self.stage_index >= 6,
            "trade": has_ship("transport") and len(game.colony_manager.colonies) >= 2 and self.stage_index >= 5,
            "automation": game.technology.technologies.get("ai_01", {}).get("state") == "completed",
            "defense": bool(game.campaign_manager.active_event and
                            game.campaign_manager.active_event.get("category") == "Небезпека"),
        }
        for key, ready in requirements.items():
            if ready:
                self.unlock(key)
        self.technology.set_research_enabled(self.is_unlocked("research"))
        self._sync_system_gates(game)

    def section_state(self, section_name):
        mechanic, reason = self.SECTION_REQUIREMENTS.get(section_name, (None, ""))
        if mechanic is None:
            return "LOCKED", "Розділ не має налаштованої умови відкриття."
        if mechanic == "progress":
            return "AVAILABLE", ""
        if not self.is_unlocked(mechanic):
            return "LOCKED", reason
        completed_stages = self.SECTION_COMPLETION.get(section_name, ())
        if completed_stages and all(stage in self.completed_tasks for stage in completed_stages):
            return "COMPLETED", "Навчальний етап цього розділу завершено."
        return "AVAILABLE", ""

    def is_unlocked(self, mechanic_id):
        return bool(self.unlocks.get(mechanic_id, False))

    def unlock(self, mechanic_id):
        if mechanic_id not in self.unlocks:
            raise KeyError(f"Unknown progression mechanic: {mechanic_id}")
        changed = not self.unlocks[mechanic_id]
        self.unlocks[mechanic_id] = True
        if changed:
            self.events.append(f"Відкрито: {self.MECHANIC_LABELS.get(mechanic_id, mechanic_id)}.")
        if mechanic_id == "research":
            self.technology.set_research_enabled(True)
        return changed

    def current_task(self):
        if self.stage_index >= len(self.stages):
            return None
        return copy.deepcopy(self.stages[self.stage_index])

    def current_objective_progress(self, game=None):
        stage = self.current_task()
        if not stage:
            return 1
        return self._objective_progress(stage["objective"], game)

    def mark_intro_seen(self):
        self.intro_seen = True
        if "opening_briefing" not in self.seen_story_events:
            self.seen_story_events.append("opening_briefing")

    def replay_explanation(self):
        stage = self.current_task()
        if not stage:
            return "Навчальний протокол завершено."
        self.explanation_history.append(stage["id"])
        return stage["description"]

    def perform_salvage(self):
        if self.salvage_used or self.stage_id != "awakening":
            return False, "Аварійний збір уже використано або це завдання неактивне."
        reward = self.balance.get("salvage_reward", self.config["salvage_reward"])
        if any(float(amount) > self.economy.get(key).free_capacity + 1e-9
               for key, amount in reward.items()):
            return False, "Недостатньо місця на складі для повного аварійного вантажу."
        accepted = {key: self.economy.add(key, float(amount)) for key, amount in reward.items()}
        self.salvage_used = True
        self.claimed_rewards.append("initial_wreckage_salvage")
        self.completed_tasks.append("awakening")
        self.commander_xp += 25
        self._recalculate_commander_level()
        self.stage_index = 1
        self.stage_id = "power"
        self.active_task_id = "power"
        self.unlock("building")
        self.events.append("Аварійний маніфест передано на склад: " +
                           ", ".join(f"{k} +{v:g}" for k,v in accepted.items() if v > 0) + ".")
        self.events.append("Завдання завершено: Пробудження.")
        self.events.append("Нове завдання: Відновлення живлення. " + self.stages[1]["description"])
        return True, "Уламки зібрано. Вантажний маніфест передано на склад."

    def _objective_progress(self, objective, game):
        kind = objective["type"]
        if kind == "salvage":
            return int(self.salvage_used)
        if game is None:
            return 0
        if kind == "building":
            return game.buildings.count(objective["id"])
        if kind == "buildings":
            return min(game.buildings.count(k) // max(1, v) for k,v in objective["items"].items())
        if kind == "mined":
            return int(game.mining.delivered_total >= objective.get("count", 1))
        if kind == "research":
            return sum(item.get("state") == "completed" for item in game.technology.technologies.values()) if game.buildings.count("laboratory") else 0
        if kind == "ship":
            return sum(s.ship_type == objective["ship_type"] for s in game.fleet.ships)
        if kind == "ships":
            return min(sum(s.ship_type == ship_type for s in game.fleet.ships) // max(1, count)
                       for ship_type, count in objective["items"].items())
        if kind == "systems":
            return sum(bool(s.get("discovered")) for s in game.galaxy.systems.values())
        if kind == "colonies":
            return len(game.colony_manager.colonies)
        if kind == "automation":
            settings = game.automation_manager.settings
            return sum(bool(v.get("enabled")) for v in settings.values() if isinstance(v, dict))
        if kind == "automation_and_colonies":
            settings = game.automation_manager.settings
            enabled = sum(bool(v.get("enabled")) for v in settings.values() if isinstance(v, dict))
            return min(enabled, len(game.colony_manager.colonies) // 2)
        if kind == "trade_route":
            return len(game.trade_manager.routes)
        return 0

    def _stage_ready(self, stage, game):
        obj = stage["objective"]
        if game is None:
            if obj["type"] == "building":
                return self.buildings.count(obj["id"]) >= obj.get("count", 1)
            return False
        if obj["type"] == "buildings":
            return all(game.buildings.count(k) >= v for k,v in obj["items"].items())
        if obj["type"] == "mined":
            return game.mining.delivered_total >= obj.get("count", 1)
        if obj["type"] == "research":
            return game.buildings.count("laboratory") >= 1 and self._objective_progress(obj, game) >= obj.get("count", 1)
        if obj["type"] == "ships":
            return all(sum(s.ship_type == ship_type for s in game.fleet.ships) >= count
                       for ship_type, count in obj["items"].items())
        if obj["type"] == "automation_and_colonies":
            return (self._objective_progress(obj, game) >= obj.get("count", 1)
                    and len(game.colony_manager.colonies) >= 2)
        if obj["type"] == "systems":
            return self._objective_progress(obj, game) >= obj.get("count", 2)
        if obj.get("requires_two_colonies") and len(game.colony_manager.colonies) < 2:
            return False
        return self._objective_progress(obj, game) >= obj.get("count", obj.get("target", 1))

    def _grant_stage_reward(self, stage):
        reward_id = f"stage:{stage['id']}"
        if reward_id in self.claimed_rewards:
            return
        reward = stage.get("reward", {})
        xp = int(reward.get("xp", 0))
        self.commander_xp += xp
        for key, amount in reward.get("resources", {}).items():
            self.economy.add(key, float(amount))
        self._recalculate_commander_level()
        self.claimed_rewards.append(reward_id)

    def update(self, game=None):
        if game is not None:
            self.refresh_section_access(game)
        stage = self.current_task()
        if not stage:
            return stage
        if game is None and stage["objective"]["type"] != "building":
            return stage
        progress = self._objective_progress(stage["objective"], game)
        self._last_objective_progress = progress
        if not self._stage_ready(stage, game):
            return stage
        if stage["id"] not in self.completed_tasks:
            self.completed_tasks.append(stage["id"])
            self.events.append(f"Завдання завершено: {stage['title']}.")
            self._grant_stage_reward(stage)
            if stage.get("unlock_message"):
                self.events.append(stage["unlock_message"])
            if stage.get("next"):
                self.stage_index += 1
                next_stage = self.stages[self.stage_index]
                self.stage_id = next_stage["id"]
                self.active_task_id = next_stage["id"]
                self.events.append(f"Нове завдання: {next_stage['title']}.")
                self.events.append(next_stage["description"])
                self._activate_stage_mechanics(game)
            else:
                self.stage_index = len(self.stages)
                self.stage_id = "empire_established"
                self.active_task_id = None
                self.events.append("Початкову кампанію завершено. Усі базові механіки імперії відкриті.")
            if game is not None:
                self._sync_system_gates(game)
                if self.stage_id == "empire_established":
                    game.campaign_manager.enabled = True
        return self.current_task()

    def _sync_system_gates(self, game):
        game.mining.auto_dispatch_enabled = self.is_unlocked("mining")
        game.automation_manager.mining.auto_dispatch_enabled = self.is_unlocked("mining")
        game.trade_manager.active = self.is_unlocked("trade")

    def _recalculate_commander_level(self):
        tuning = self.balance.get("commander_xp_thresholds", {})
        first = int(tuning.get("first_level", 100))
        increment = int(tuning.get("per_level_increment", 75))
        level, xp, threshold = 1, self.commander_xp, first
        while xp >= threshold:
            xp -= threshold
            level += 1
            threshold = first + (level - 1) * increment
        self.commander_level = level

    def take_events(self):
        result, self.events = self.events[:], []
        return result

    def snapshot(self):
        return {
            "version": 3, "stage_index": self.stage_index, "stage_id": self.stage_id,
            "commander_level": self.commander_level, "commander_xp": self.commander_xp,
            "active_task_id": self.active_task_id, "completed_tasks": list(self.completed_tasks),
            "claimed_rewards": list(self.claimed_rewards), "seen_story_events": list(self.seen_story_events),
            "unlocks": copy.deepcopy(self.unlocks), "salvage_used": self.salvage_used,
            "intro_seen": self.intro_seen, "explanation_history": list(self.explanation_history)
        }

    def restore(self, state):
        if not isinstance(state, dict) or not state:
            # Legacy sandbox saves retain their former open access.
            for key in self.unlocks:
                self.unlocks[key] = True
            self.stage_index = len(self.stages)
            self.stage_id = "legacy_campaign"
            self.active_task_id = None
            self.salvage_used = True
            self.intro_seen = True
            self.technology.set_research_enabled(True)
            return
        # Migrate the previous two-step progression save format without resetting the slot.
        if int(state.get("version", 1)) < 2:
            legacy_stage = state.get("stage_id", "awakening")
            legacy_task = state.get("active_task_id")
            migrated_index = 1 if legacy_stage == "first_power" or legacy_task == "restore_power" else 0
            if legacy_stage == "legacy_campaign":
                migrated_index = len(self.stages)
            self.stage_index = migrated_index
        else:
            self.stage_index = max(0, min(int(state.get("stage_index", 0)), len(self.stages)))
        default_stage = self.stages[self.stage_index]["id"] if self.stage_index < len(self.stages) else "empire_established"
        self.stage_id = str(state.get("stage_id", default_stage))
        if int(state.get("version", 1)) < 2 and self.stage_index == 1:
            self.stage_id = "power"
        self.commander_xp = max(0, int(state.get("commander_xp", 0)))
        self.commander_level = max(1, int(state.get("commander_level", 1)))
        self.active_task_id = state.get("active_task_id")
        if int(state.get("version", 1)) < 2:
            self.active_task_id = self.stage_id if self.stage_index < len(self.stages) else None
        self.completed_tasks = list(dict.fromkeys(state.get("completed_tasks", [])))
        if self.stage_index >= 1 and "awakening" not in self.completed_tasks:
            self.completed_tasks.append("awakening")
        self.claimed_rewards = list(dict.fromkeys(state.get("claimed_rewards", [])))
        self.seen_story_events = list(dict.fromkeys(state.get("seen_story_events", [])))
        self.explanation_history = list(dict.fromkeys(state.get("explanation_history", [])))
        if int(state.get("version", 1)) >= 3:
            for key, value in state.get("unlocks", {}).items():
                if key in self.unlocks:
                    self.unlocks[key] = bool(value)
        else:
            # Older progression saves unlocked whole groups by chapter. Rebuild
            # access from actual restored buildings/ships/technology instead.
            self.unlocks = {key: key in ("overview", "campaign", "settings")
                            for key in self.MECHANIC_LABELS}
            self.technology.set_research_enabled(False)
        self.salvage_used = bool(state.get("salvage_used", "initial_wreckage_salvage" in self.claimed_rewards or self.stage_index >= 1))
        self.intro_seen = bool(state.get("intro_seen", False))
        self.technology.set_research_enabled(self.is_unlocked("research"))
