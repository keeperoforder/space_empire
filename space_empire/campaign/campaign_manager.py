"""JSON-driven campaign missions and random story events."""
import copy, json, random
from pathlib import Path

class CampaignManager:
    def __init__(self,economy,buildings,mining,fleet,technology,galaxy,colonies,data_path=None,rng=None,enabled=True):
        self.economy,self.buildings,self.mining=economy,buildings,mining
        self.fleet,self.technology,self.galaxy,self.colonies=fleet,technology,galaxy,colonies
        path=Path(data_path) if data_path else Path(__file__).with_name("campaign.json")
        self.data=json.loads(path.read_text(encoding="utf-8"))
        self.chapters=self.data["chapters"]
        self.missions={m["id"]:copy.deepcopy(m) for m in self.data["missions"]}
        self.event_definitions=self.data["events"]
        self.rng=rng or random.Random()
        self.flags=set(); self.active_event=None; self.timer=float(self.data["event_settings"]["first_event_delay"])
        self.events=[]
        self.enabled=bool(enabled)
        if self.enabled:
            self._recalculate()

    def _progress(self,o):
        t=o["type"]
        if t=="resource": return self.economy.get(o["key"]).amount
        if t=="building": return sum(len(v) for k,v in self.buildings.owned.items() if k==o["key"])
        if t=="mined": return getattr(self.mining,"delivered_total",0)
        if t=="ship": return sum(s.ship_type==o["key"] for s in self.fleet.ships)
        if t=="fleet": return len(self.fleet.ships)
        if t=="systems": return sum(bool(s.get("discovered")) for s in self.galaxy.systems.values())
        if t=="colonies": return len(getattr(self.colonies,"colonies",[]))
        if t=="colony_level":
            rows=getattr(self.colonies,"colonies",{})
            values=rows.values() if isinstance(rows,dict) else rows
            return max([int(c.get("development",c.get("level",1))) for c in values] or [0])
        if t=="flag": return int(o["key"] in self.flags)
        if t=="tech_count": return sum(v.get("state")=="completed" for v in self.technology.technologies.values())
        if t=="tech_keyword":
            return int(any(v.get("state")=="completed" and any(k in (key+" "+str(v.get("name",""))).lower() for k in o["keys"]) for key,v in self.technology.technologies.items()))
        return 0

    def _recalculate(self):
        if not self.enabled:
            return
        if getattr(self, "developer_unlock_all", False):
            for m in self.missions.values():
                if m.get("status") == "completed":
                    continue
                m["status"] = "available"
                m["progress"] = self._progress(m["objective"])
                if m["progress"] >= m["objective"].get("amount", 1):
                    m["status"] = "completed"
                    for key, value in m.get("rewards", {}).items():
                        self.economy.add(key, value)
                    self.events.append("Місію завершено: " + m["title"] + ". Нагороди нараховано.")
            return
        for chapter in self.chapters:
            previous=all(all(self.missions[mid]["status"]=="completed" for mid in c["missions"]) for c in self.chapters[:self.chapters.index(chapter)])
            for mid in chapter["missions"]:
                m=self.missions[mid]
                if m.get("status")=="completed": continue
                earlier=chapter["missions"][:chapter["missions"].index(mid)]
                m["status"]="available" if previous and all(self.missions[x]["status"]=="completed" for x in earlier) else "locked"
                m["progress"]=self._progress(m["objective"])
                if m["status"]=="available" and m["progress"]>=m["objective"].get("amount",1):
                    m["status"]="completed"
                    for key,value in m.get("rewards",{}).items(): self.economy.add(key,value)
                    self.events.append("Місію завершено: "+m["title"]+". Нагороди нараховано.")
        # Refresh next mission statuses after completion cascade.
        for chapter in self.chapters:
            previous=all(all(self.missions[mid]["status"]=="completed" for mid in c["missions"]) for c in self.chapters[:self.chapters.index(chapter)])
            for i,mid in enumerate(chapter["missions"]):
                m=self.missions[mid]
                if m["status"]!="completed":
                    m["status"]="available" if previous and all(self.missions[x]["status"]=="completed" for x in chapter["missions"][:i]) else "locked"

    def current_chapter(self):
        if not self.chapters:
            return None
        return next((c for c in self.chapters
                     if not all(self.missions[x]["status"] == "completed"
                                for x in c.get("missions", [])
                                if x in self.missions)), self.chapters[-1])

    def update(self,dt):
        if not self.enabled:
            return
        self._recalculate()
        if self.active_event: return
        self.timer-=max(0,float(dt))
        if self.timer<=0:
            self.trigger_event()
            cfg=self.data["event_settings"]
            self.timer=self.rng.uniform(cfg["minimum_interval"],cfg["maximum_interval"])

    def trigger_event(self,event_id=None):
        if self.active_event: return False
        event=next((x for x in self.event_definitions if x["id"]==event_id),None) if event_id else self.rng.choice(self.event_definitions)
        if not event: return False
        self.active_event=copy.deepcopy(event)
        self.events.append("Космічна подія: "+event["title"])
        return True

    def choose_event(self,choice_id):
        if not self.active_event: return False,"Немає активної події."
        choice=next((x for x in self.active_event["choices"] if x["id"]==choice_id),None)
        if not choice: return False,"Невідомий варіант."
        costs=choice.get("costs",{})
        if not self.economy.can_afford(costs): return False,"Недостатньо ресурсів."
        if costs and not self.economy.spend(costs): return False,"Не вдалося списати ресурси."
        for key,value in choice.get("effects",{}).items():
            self.economy.add(key,value) if value>=0 else setattr(self.economy.get(key),"amount",max(0,self.economy.get(key).amount+value))
        self.flags.update(choice.get("flags",[]))
        self.events.append("Рішення: "+self.active_event["title"]+" — "+choice["label"])
        self.active_event=None; self._recalculate()
        return True,"Рішення виконано."

    def snapshot(self):
        return {"missions":copy.deepcopy(self.missions),"flags":sorted(self.flags),"active_event":copy.deepcopy(self.active_event),"timer":self.timer,"rng_state":self.rng.getstate(),"enabled":self.enabled}

    def restore(self,state):
        self.enabled=bool(state.get("enabled", True))
        for key,value in state.get("missions",{}).items():
            if key in self.missions: self.missions[key].update({k:copy.deepcopy(value[k]) for k in ("status","progress") if k in value})
        self.flags=set(state.get("flags",[])); self.active_event=copy.deepcopy(state.get("active_event"))
        self.timer=max(0,float(state.get("timer",self.timer)))
        try:
            if state.get("rng_state"): self.rng.setstate(state["rng_state"])
        except (TypeError,ValueError): pass
        self._recalculate()

    def take_events(self):
        result,self.events=self.events[:],[]
        return result
