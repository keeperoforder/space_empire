"""Player market and recurring interplanetary trade routes."""
from __future__ import annotations
import copy, json, math
from pathlib import Path

class TradeManager:
    def __init__(self, economy, fleet, colonies, market_path=None):
        self.economy,self.fleet,self.colonies=economy,fleet,colonies
        path=Path(market_path) if market_path else Path(__file__).with_name("market.json")
        self.prices=json.loads(path.read_text(encoding="utf-8"))
        self.routes=[]; self._next_route=1; self.events=[]; self.active=True

    def buy(self, resource, quantity):
        quantity=float(quantity)
        if resource not in self.prices or not math.isfinite(quantity) or quantity<=0:
            return False,"Некоректна торгова операція."
        cost=quantity*self.prices[resource]
        if self.economy.get(resource).amount + quantity > self.economy.get(resource).capacity:
            return False,"Недостатньо місця на складі."
        if not self.economy.spend({"credits":cost}):return False,"Недостатньо кредитів."
        accepted=self.economy.add(resource,quantity)
        if accepted+1e-7<quantity:
            self.economy.add("credits",cost)
            return False,"Склад не прийняв повний обсяг."
        self.events.append(f"Ринок: придбано {quantity:g} {resource} за {cost:g} кредитів.")
        return True,f"Придбано {quantity:g} {resource}."

    def sell(self, resource, quantity):
        quantity=float(quantity)
        if resource not in self.prices or not math.isfinite(quantity) or quantity<=0:
            return False,"Некоректна торгова операція."
        stock=self.economy.get(resource)
        credit_stock=self.economy.get("credits")
        credit_room=max(0.0,credit_stock.capacity-credit_stock.amount)
        max_sell=credit_room/(self.prices[resource]*0.82)
        quantity=min(quantity,max_sell)
        if quantity<=0:return False,"На складі кредитів немає місця для виручки."
        if stock.amount+1e-9<quantity:return False,"Недостатньо ресурсу для продажу."
        stock.spend(quantity)
        revenue=quantity*self.prices[resource]*0.82
        self.economy.add("credits",revenue)
        self.events.append(f"Ринок: продано {quantity:g} {resource}, прибуток {revenue:g} кредитів.")
        return True,f"Продано {quantity:g} {resource} за {revenue:g} кредитів."

    def create_route(self, source_planet, destination_planet, resource, quantity, ship_id, interval=180.0, enabled=True):
        if source_planet not in self.colonies.colonies or destination_planet not in self.colonies.colonies:
            return False,"Для маршруту обидві планети мають бути колонізовані."
        if source_planet==destination_planet or resource not in self.prices:
            return False,"Некоректні точки або ресурс маршруту."
        ship=next((s for s in self.fleet.ships if s.id==ship_id and s.ship_type=="transport"),None)
        if not ship:return False,"Оберіть транспортний корабель."
        if quantity<=0 or interval<10:return False,"Обсяг має бути додатним, інтервал — не менше 10 секунд."
        rid=f"trade-{self._next_route:03d}";self._next_route+=1
        self.routes.append({"id":rid,"source":source_planet,"destination":destination_planet,
                            "resource":resource,"quantity":float(quantity),"ship_id":ship_id,
                            "interval":float(interval),"timer":0.0,"enabled":bool(enabled),
                            "in_flight":False,"cargo":0.0})
        self.events.append(f"Створено торговельний маршрут {rid}.")
        return True,rid

    def toggle_route(self, route_id, enabled):
        route=next((r for r in self.routes if r["id"]==route_id),None)
        if not route:return False,"Маршрут не знайдено."
        route["enabled"]=bool(enabled);return True,"Стан маршруту змінено."

    def remove_route(self, route_id):
        route=next((r for r in self.routes if r["id"]==route_id),None)
        if route and route["in_flight"]:
            return False,"Не можна видалити маршрут, поки корабель виконує рейс."
        self.routes=[r for r in self.routes if r["id"]!=route_id]
        return True,"Маршрут видалено."

    def _dispatch(self, route):
        ship=next((s for s in self.fleet.ships if s.id==route["ship_id"]),None)
        if not ship or ship.status!="ready" or ship.task!="idle":return False
        source=self.colonies.colonies[route["source"]]
        target=self.colonies.colonies[route["destination"]]
        src_stock=source["economy"][route["resource"]]
        dst_stock=target["economy"][route["resource"]]
        reserved=float(dst_stock.get("reserved_capacity",0.0))
        qty=min(route["quantity"],ship.cargo_capacity,src_stock["amount"],
                max(0.0,dst_stock["capacity"]-dst_stock["amount"]-reserved))
        if qty<=0:return False
        src_planet=self.colonies.planets[route["source"]]
        dst_planet=self.colonies.planets[route["destination"]]
        a=self.colonies.galaxy.systems[src_planet["system_id"]]
        b=self.colonies.galaxy.systems[dst_planet["system_id"]]
        # Explicit two-stop itinerary: station -> source colony -> destination colony -> station.
        d1=math.hypot(a["x"]-ship.x,a["y"]-ship.y)
        d2=math.hypot(b["x"]-a["x"],b["y"]-a["y"])
        d3=math.hypot(b["x"],b["y"])
        fuel=(d1+d2+d3)*ship.spec["fuel_rate"]*self.fleet.technology_bonuses.get("ship_fuel_multiplier",1.0)
        if not self.economy.spend({"fuel":fuel}):return False
        ship.task="transport";ship.status="outbound"
        ship.target_x,ship.target_y=float(a["x"]),float(a["y"])
        ship.target_name=source["name"]
        ship.mission_elapsed=0.0
        speed_mult=self.fleet.technology_bonuses.get("fleet_mission_speed_multiplier",1.0)
        ship.mission_duration=max(1.0,2.0/speed_mult)
        ship.fuel_consumed+=fuel
        ship.metadata["trade_route_stage"]="to_source"
        ship.metadata["trade_destination"]={"x":float(b["x"]),"y":float(b["y"]),"name":target["name"]}
        src_stock["amount"]-=qty
        dst_stock["reserved_capacity"]=reserved+qty
        ship.metadata["trade_route_id"]=route["id"]
        route["cargo"]=qty;route["in_flight"]=True;route["timer"]=0.0
        return True

    def update(self,dt):
        for route in self.routes:
            if route["in_flight"]:
                ship=next((s for s in self.fleet.ships if s.id==route["ship_id"]),None)
                if ship and ship.status=="ready" and ship.task=="idle" and ship.metadata.get("trade_route_id")==route["id"]:
                    dst=self.colonies.colonies.get(route["destination"])
                    if dst:
                        row=dst["economy"][route["resource"]]
                        reserved=float(row.get("reserved_capacity",0.0))
                        row["reserved_capacity"]=max(0.0,reserved-route["cargo"])
                        accepted=min(route["cargo"],max(0.0,row["capacity"]-row["amount"]))
                        row["amount"]+=accepted
                        self.events.append(f"Маршрут {route['id']}: доставлено {accepted:g} {route['resource']}.")
                    for key in ("trade_route_id","trade_route_stage","trade_destination"):
                        ship.metadata.pop(key,None)
                    route["in_flight"]=False;route["cargo"]=0.0
            elif self.active and route["enabled"]:
                route["timer"]+=dt
                if route["timer"]>=route["interval"]:
                    if self._dispatch(route):route["timer"]=0.0

    def take_events(self):
        out,self.events=self.events,[]
        return out
    def snapshot(self):
        return {"routes":copy.deepcopy(self.routes),"next_route":self._next_route}
    def restore(self,data):
        self.routes=copy.deepcopy(data.get("routes",[]))
        self._next_route=int(data.get("next_route",len(self.routes)+1))
