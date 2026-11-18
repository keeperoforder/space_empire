"""Extensible rule-based automation engine."""
from __future__ import annotations
import copy

DEFAULT_SETTINGS={
 "auto_build":{"enabled":False,"rules":[{"building_id":"solar_array","resource":"energy","below":180,"priority":1},
     {"building_id":"smelter","resource":"metal","below":250,"priority":2}]},
 "auto_upgrade":{"enabled":False,"max_level":3,"priority":3},
 "mining":{"enabled":True,"prefer_rich_asteroids":True,"fuel_reserve":60,"priority":1},
 "transport":{"enabled":False,"threshold":500,"quantity":150,"priority":4},
 "fuel":{"enabled":True,"reserve":100,"buy_below_reserve":True,"priority":0},
 "colonies":{"enabled":False,"auto_base":True,"auto_develop":False,"development_limit":3,"transport_surplus":True,"priority":5},
 "trade":{"enabled":False,"priority":6},
 "production_priorities":{"energy":1,"metal":2,"crystals":3,"fuel":4,"credits":5,"science":6}
}

class AutomationManager:
    def __init__(self,economy,buildings,mining,fleet,colonies,trade):
        self.economy,self.buildings,self.mining,self.fleet,self.colonies,self.trade=economy,buildings,mining,fleet,colonies,trade
        self.settings=copy.deepcopy(DEFAULT_SETTINGS);self.events=[]
        self._clock=0.0;self._cooldowns={}
        self.recipes={}
        self.custom_processes={}
        self.mining.dispatch_fuel_reserve=float(self.settings["mining"]["fuel_reserve"])
    def set_enabled(self,process,enabled):
        if process not in self.settings:raise KeyError(process)
        self.settings[process]["enabled"]=bool(enabled)
        if process=="mining":
            self.mining.auto_dispatch_enabled=bool(enabled)
            self.mining.dispatch_fuel_reserve=float(self.settings["mining"]["fuel_reserve"]) if enabled else 0.0
        elif process=="trade":
            self.trade.active=bool(enabled)
    def set_priority(self,resource,priority):
        if resource not in self.settings["production_priorities"]:raise KeyError(resource)
        self.settings["production_priorities"][resource]=max(1,min(99,int(priority)))
    def register_recipe(self,recipe_id,inputs,outputs,duration,priority=50,enabled=False):
        """Register an extensible production-chain recipe.

        Inputs are consumed atomically when a batch starts. Outputs are emitted
        only when every destination resource has enough free storage.
        """
        import math
        if not recipe_id or recipe_id in self.recipes:raise ValueError("recipe_id must be unique and non-empty")
        duration=float(duration)
        if not math.isfinite(duration) or duration<=0:raise ValueError("duration must be positive")
        for mapping in (inputs,outputs):
            if not mapping:raise ValueError("recipe inputs and outputs cannot be empty")
            for key,value in mapping.items():
                self.economy.get(key)
                if not math.isfinite(float(value)) or float(value)<=0:raise ValueError("recipe quantities must be positive")
        self.recipes[recipe_id]={"inputs":dict(inputs),"outputs":dict(outputs),"duration":duration,
                                 "elapsed":0.0,"priority":int(priority),"enabled":bool(enabled),
                                 "running":False,"completed_batches":0}
    def set_recipe_enabled(self,recipe_id,enabled):
        self.recipes[recipe_id]["enabled"]=bool(enabled)
    def register_process(self,name,handler,enabled=False):
        """Register a custom automation callback for future production systems."""
        if not name or name in self.custom_processes:raise ValueError("process name must be unique and non-empty")
        if not callable(handler):raise TypeError("handler must be callable")
        self.custom_processes[name]={"handler":handler,"enabled":bool(enabled)}
    def _update_recipes(self,dt):
        for recipe_id,recipe in sorted(self.recipes.items(),key=lambda item:item[1]["priority"]):
            if not recipe["enabled"]:continue
            if not recipe["running"]:
                if not self.economy.can_afford(recipe["inputs"]):continue
                if not self.economy.spend(recipe["inputs"]):continue
                recipe["running"]=True;recipe["elapsed"]=0.0
            recipe["elapsed"]=min(recipe["duration"],recipe["elapsed"]+dt)
            if recipe["elapsed"]+1e-9<recipe["duration"]:continue
            if any(self.economy.get(k).amount+v>self.economy.get(k).capacity+1e-9
                   for k,v in recipe["outputs"].items()):
                recipe["elapsed"]=recipe["duration"]
                continue
            for key,value in recipe["outputs"].items():self.economy.add(key,value)
            recipe["completed_batches"]+=1;recipe["running"]=False;recipe["elapsed"]=0.0
            self.events.append(f"Виробничий ланцюжок {recipe_id}: завершено партію {recipe['completed_batches']}.")
    def _ready(self,key,period=5.0):
        if self._cooldowns.get(key,0)>0:return False
        self._cooldowns[key]=period;return True
    def _auto_build(self):
        cfg=self.settings["auto_build"]
        if not cfg["enabled"] or len(self.buildings.constructions)>=2 or not self._ready("build"):return
        rules=sorted(cfg["rules"],key=lambda r:(self.settings["production_priorities"].get(r["resource"],99),r.get("priority",99)))
        active={p.building_id for p in self.buildings.constructions}
        for rule in rules:
            res=self.economy.get(rule["resource"])
            if res.amount>=rule["below"] or rule["building_id"] in active:continue
            ok,msg=self.buildings.start_build(rule["building_id"])
            if ok:self.events.append("Автобудівництво: "+msg);break
    def _auto_upgrade(self):
        cfg=self.settings["auto_upgrade"]
        if not cfg["enabled"] or self.buildings.constructions or not self._ready("upgrade",12):return
        choices=[]
        for bid,instances in self.buildings.owned.items():
            cost=self.buildings.next_upgrade_cost(bid)
            if cost and instances and instances[0]["level"]<cfg["max_level"]:
                choices.append((self.settings["production_priorities"].get(next(iter(self.buildings.definition(bid).get("production",{})), "metal"),99),bid))
        for _,bid in sorted(choices):
            ok,msg=self.buildings.start_upgrade(bid)
            if ok:self.events.append("Автоапгрейд: "+msg);break
    def _auto_fuel(self):
        cfg=self.settings["fuel"]
        if not cfg["enabled"] or not cfg.get("buy_below_reserve") or not self._ready("fuel",30):return
        fuel=self.economy.get("fuel")
        if fuel.amount>=cfg["reserve"]:return
        quantity=min(cfg["reserve"]+100-fuel.amount,fuel.capacity-fuel.amount)
        if quantity<=0:return
        ok,msg=self.trade.buy("fuel",quantity)
        if ok:self.events.append("Автопоповнення палива: "+msg)
    def _auto_mining(self):
        cfg=self.settings["mining"]
        self.mining.auto_dispatch_enabled=bool(cfg["enabled"])
        self.mining.dispatch_fuel_reserve=float(cfg["fuel_reserve"]) if cfg["enabled"] else 0.0
        if not cfg["enabled"]:return
        # MiningManager already performs dispatch/return cycles. This policy only
        # redirects idle ships from depleted fields and respects central fuel reserve.
        if self.economy.get("fuel").amount<cfg["fuel_reserve"]:return
        for ship in self.mining.ships:
            if ship.task!="docked":continue
            candidates=[a for a in self.mining.asteroids.values() if a.reserve>0]
            if not candidates:continue
            target=max(candidates,key=lambda a:a.reserve*a.richness) if cfg["prefer_rich_asteroids"] else candidates[0]
            if ship.assigned_target_id!=target.id:
                self.mining.assign_ship(ship.id,target.id)
    def _auto_colonies(self):
        cfg=self.settings["colonies"]
        if not cfg["enabled"] or not self._ready("colonies",15):return
        for pid,colony in self.colonies.colonies.items():
            if cfg["auto_base"] and not colony["base_built"]:
                ok,msg=self.colonies.build_base(pid)
                if ok:self.events.append("Автоколонізація: "+msg)
                continue
            if cfg["auto_develop"] and colony["base_level"]<cfg["development_limit"]:
                ok,msg=self.colonies.develop(pid)
                if ok:self.events.append("Автоколонізація: "+msg)
    def _auto_transport(self):
        cfg=self.settings["transport"]
        if not cfg["enabled"] or not self._ready("transport",20):return
        ships=[s for s in self.fleet.ships if s.ship_type=="transport" and s.status=="ready" and s.task=="idle" and not s.metadata]
        if not ships:return
        for pid,colony in self.colonies.colonies.items():
            if not colony["base_built"]:continue
            for resource,row in colony["economy"].items():
                if row["amount"]>=cfg["threshold"]:
                    ok,msg=self.colonies.transfer_to_station(pid,ships[0].id,resource,min(cfg["quantity"],row["amount"]))
                    if ok:self.events.append("Автотранспорт: "+msg);return
    def update(self,dt):
        for key in list(self._cooldowns):self._cooldowns[key]=max(0.0,self._cooldowns[key]-dt)
        self._auto_build();self._auto_upgrade();self._auto_fuel();self._auto_mining();self._auto_colonies();self._auto_transport()
        self._update_recipes(dt)
        for name,process in self.custom_processes.items():
            if process["enabled"]:process["handler"](dt,self)
        # The trade manager handles route clocks independently; this switch is a master gate.
        self.trade.active=bool(self.settings["trade"]["enabled"])
    def take_events(self):
        out,self.events=self.events,[]
        return out
    def snapshot(self):
        return {"settings":copy.deepcopy(self.settings),"clock":self._clock,"cooldowns":dict(self._cooldowns),
                "recipes":copy.deepcopy(self.recipes),
                "custom_processes":{name:{"enabled":p["enabled"]} for name,p in self.custom_processes.items()}}
    def restore(self,data):
        for key,value in data.get("settings",{}).items():
            if key in self.settings and isinstance(value,dict):self.settings[key].update(copy.deepcopy(value))
        self._clock=float(data.get("clock",0));self._cooldowns=dict(data.get("cooldowns",{}))
        for recipe_id,state in data.get("recipes",{}).items():
            if recipe_id in self.recipes:
                for key in ("elapsed","enabled","running","completed_batches"):
                    if key in state:self.recipes[recipe_id][key]=copy.deepcopy(state[key])
        for name,state in data.get("custom_processes",{}).items():
            if name in self.custom_processes:self.custom_processes[name]["enabled"]=bool(state.get("enabled",False))
        self.mining.auto_dispatch_enabled=bool(self.settings["mining"]["enabled"])
        self.mining.dispatch_fuel_reserve=float(self.settings["mining"]["fuel_reserve"]) if self.settings["mining"]["enabled"] else 0.0
        self.trade.active=bool(self.settings["trade"]["enabled"])
