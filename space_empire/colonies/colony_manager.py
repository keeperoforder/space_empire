"""Planet discovery, colonization missions and independent colony economies."""
from __future__ import annotations
import copy, json, math
from pathlib import Path

try:
    _economy_costs = json.loads((Path(__file__).resolve().parents[1] / "balance" / "economy_costs.json").read_text(encoding="utf-8"))
except (OSError, ValueError, TypeError):
    _economy_costs = {}

class ColonyManager:
    COLONIZE_COST = dict(_economy_costs.get("colonization", {"metal": 260, "energy": 120, "crystals": 35, "fuel": 55, "credits": 240}))
    BASE_COST = dict(_economy_costs.get("colony_base", {"metal": 180, "energy": 80, "crystals": 18, "credits": 120}))
    RESOURCE_KEYS = ("metal", "energy", "crystals", "fuel", "credits", "science")

    def __init__(self, galaxy, fleet, resources, catalog_path=None):
        self.galaxy, self.fleet, self.resources = galaxy, fleet, resources
        path = Path(catalog_path) if catalog_path else Path(__file__).with_name("planet_types.json")
        self.types = json.loads(path.read_text(encoding="utf-8"))
        self.planets = {}
        self.colonies = {}
        self.missions = {}
        self.events = []
        self._discover_from_galaxy()

    def _discover_from_galaxy(self):
        for system in self.galaxy.systems.values():
            for obj in system.get("objects", []):
                if obj.get("type") != "Планета": continue
                pid = obj["id"]
                if pid in self.planets: continue
                type_ids = list(self.types)
                idx = sum(ord(c) for c in pid) % len(type_ids)
                type_id = type_ids[idx]
                spec = self.types[type_id]
                size = 0.65 + (sum(ord(c) for c in pid+"size") % 70)/100
                self.planets[pid] = {
                    "id":pid, "name":obj["name"], "system_id":system["id"],
                    "type":type_id, "size":round(size,2),
                    "resource_characteristics":copy.deepcopy(spec["resources"]),
                    "population":0.0, "development":0,
                    "colonization_potential":round(spec["habitability"] * (0.7 + size*0.3),3),
                    "discovered":bool(system.get("discovered") and obj.get("revealed")),
                    "colonized":False
                }

    def refresh_discoveries(self):
        self._discover_from_galaxy()
        for pid, planet in self.planets.items():
            system = self.galaxy.systems[planet["system_id"]]
            obj = next((o for o in system["objects"] if o["id"] == pid), None)
            if system.get("discovered") and obj and obj.get("revealed"):
                planet["discovered"] = True

    def available_colonizers(self):
        return [s for s in self.fleet.ships if s.ship_type=="colonizer" and s.status=="ready" and s.task=="idle"]

    def colonize(self, planet_id, ship_id=None):
        self.refresh_discoveries()
        p = self.planets[planet_id]
        if not p["discovered"]: return False, "Планета ще не відкрита розвідкою."
        if p["colonized"] or planet_id in self.missions.values(): return False, "Планета вже колонізована або місія триває."
        if p["type"] == "gas_giant": return False, "Газові гіганти непридатні для наземної колонії; потрібна орбітальна платформа."
        ships = self.available_colonizers()
        ship = next((s for s in ships if ship_id is None or s.id==ship_id),None)
        if not ship: return False, "Потрібен вільний корабель-колонізатор."
        if not self.resources.spend(self.COLONIZE_COST): return False, "Недостатньо ресурсів для колонізаційної місії."
        system = self.galaxy.systems[p["system_id"]]
        distance = math.hypot(system["x"],system["y"])
        ok,msg = self.fleet.assign_task(ship.id,"colonize",system["x"],system["y"],p["name"],duration=35+distance*0.02)
        if not ok:
            # Fleet assignment charges fuel only; refund the other costs.
            for k,v in self.COLONIZE_COST.items():
                if k!="fuel": self.resources.add(k,v)
            return False,msg
        ship.metadata["colony_planet_id"] = planet_id
        self.missions[ship.id] = planet_id
        self.events.append(f"Колонізатор вирушив до планети {p['name']}.")
        return True, f"Місію колонізації планети {p['name']} розпочато."

    def _found_colony(self, planet, ship):
        ptype = self.types[planet["type"]]
        self.colonies[planet["id"]] = {
            "planet_id":planet["id"], "name":planet["name"], "population":max(100.0,ptype["population"]*1000),
            "development":1, "base_level":0, "base_built":False,
            "economy":{k:{"amount":0.0,"capacity":1000.0,"production":0.0,"consumption":0.0} for k in self.RESOURCE_KEYS},
            "transport_cooldown":0.0, "production_clock":0.0
        }
        planet["colonized"]=True
        planet["population"]=self.colonies[planet["id"]]["population"]
        planet["development"]=1
        ship.metadata.pop("colony_planet_id",None)
        self.events.append(f"Засновано колонію: {planet['name']}. Побудуйте базу для запуску виробництва.")

    def build_base(self, planet_id):
        colony=self.colonies.get(planet_id)
        if not colony: return False,"Колонії не існує."
        if colony["base_built"]: return False,"Базу вже побудовано."
        if not self.resources.spend(self.BASE_COST): return False,"Недостатньо ресурсів для будівництва бази."
        colony["base_built"]=True; colony["base_level"]=1
        self._configure_economy(colony)
        self.events.append(f"На планеті {colony['name']} збудовано базу.")
        return True,"Планетарну базу збудовано."

    def develop(self, planet_id):
        colony=self.colonies.get(planet_id)
        if not colony or not colony["base_built"]: return False,"Спочатку побудуйте базу."
        cost={"metal":120*colony["base_level"],"energy":65*colony["base_level"],"crystals":15*colony["base_level"],"credits":90*colony["base_level"]}
        if not self.resources.spend(cost): return False,"Недостатньо ресурсів для розвитку."
        colony["base_level"]+=1; colony["development"]+=1
        colony["population"]*=1.18
        self.planets[planet_id]["population"]=colony["population"]
        self.planets[planet_id]["development"]=colony["development"]
        self._configure_economy(colony)
        self.events.append(f"Колонію {colony['name']} розвинено до рівня {colony['development']}.")
        return True,"Рівень колонії підвищено."

    def _configure_economy(self,colony):
        p=self.planets[colony["planet_id"]]
        mult=self.types[p["type"]]["resources"]
        lvl=colony["base_level"]
        base={"metal":0.32,"energy":0.28,"crystals":0.10,"fuel":0.07,"credits":0.18,"science":0.035}
        for key in self.RESOURCE_KEYS:
            row=colony["economy"][key]
            row["production"]=base[key]*mult.get(key,1.0)*lvl
            row["capacity"]=1000.0*lvl

    def transfer_to_station(self, planet_id, ship_id, resource_key, amount):
        colony=self.colonies.get(planet_id)
        if not colony or not colony["base_built"]: return False,"Колонія не має діючої бази."
        ship=next((s for s in self.fleet.ships if s.id==ship_id),None)
        if not ship or ship.ship_type!="transport" or ship.status!="ready" or ship.task!="idle":
            return False,"Потрібен вільний транспортний корабель."
        if resource_key not in self.RESOURCE_KEYS or amount<=0: return False,"Некоректний вантаж."
        stock=colony["economy"][resource_key]
        station_stock=self.resources.get(resource_key)
        station_free=max(0.0,station_stock.capacity-station_stock.amount)
        qty=min(float(amount),stock["amount"],ship.cargo_capacity,station_free)
        if qty<=0:return False,"Немає ресурсу або вільного місця на складі станції."
        system=self.galaxy.systems[self.planets[planet_id]["system_id"]]
        ok,msg=self.fleet.assign_task(ship.id,"transport",system["x"],system["y"],colony["name"],duration=2.0)
        if not ok:return False,msg
        stock["amount"]-=qty
        ship.metadata["colony_transfer"]={"planet_id":planet_id,"resource":resource_key,"amount":qty}
        return True,f"Транспорт забирає {qty:.1f} од. ресурсу «{resource_key}»."

    def update(self,dt):
        self.refresh_discoveries()
        for ship_id,planet_id in list(self.missions.items()):
            ship=next((s for s in self.fleet.ships if s.id==ship_id),None)
            if not ship: continue
            if ship.status=="working" and not self.planets[planet_id]["colonized"]:
                self._found_colony(self.planets[planet_id],ship)
                del self.missions[ship_id]
        for ship in self.fleet.ships:
            transfer=ship.metadata.get("colony_transfer")
            if transfer and ship.status=="ready" and ship.task=="idle":
                self.resources.add(transfer["resource"],transfer["amount"])
                ship.metadata.pop("colony_transfer",None)
                self.events.append(f"Доставлено з колонії: {transfer['amount']:.1f} {transfer['resource']}.")
        for colony in self.colonies.values():
            if not colony["base_built"]: continue
            for key,row in colony["economy"].items():
                effective_capacity=max(0.0,row["capacity"]-row.get("reserved_capacity",0.0))
                row["amount"]=min(effective_capacity,row["amount"]+row["production"]*dt)
            colony["population"]+=colony["population"]*0.000002*dt*colony["development"]
            self.planets[colony["planet_id"]]["population"]=colony["population"]

    def take_events(self):
        out,self.events=self.events,[]
        return out

    def snapshot(self):
        return {"planets":copy.deepcopy(self.planets),"colonies":copy.deepcopy(self.colonies),
                "missions":copy.deepcopy(self.missions)}

    def restore(self,data):
        if not isinstance(data,dict):return
        for pid,state in data.get("planets",{}).items():
            if pid in self.planets:self.planets[pid].update(copy.deepcopy(state))
        self.colonies=copy.deepcopy(data.get("colonies",{}))
        self.missions=copy.deepcopy(data.get("missions",{}))
