"""Static progression graph and resource affordability audit."""
from __future__ import annotations
import json
from pathlib import Path


def load_data(root=None):
    base = Path(root) if root else Path(__file__).resolve().parents[1]
    balance = json.loads((base / "balance" / "progression_balance.json").read_text(encoding="utf-8"))
    costs = json.loads((base / "balance" / "economy_costs.json").read_text(encoding="utf-8"))
    graph = json.loads((base / "progression" / "progression_graph.json").read_text(encoding="utf-8"))
    buildings = json.loads((base / "buildings" / "catalog.json").read_text(encoding="utf-8"))
    return balance, costs, graph, buildings


def validate_graph(graph):
    nodes = {node["id"] for node in graph["nodes"]}
    if len(nodes) != len(graph["nodes"]):
        raise ValueError("Duplicate progression graph node.")
    indegree = {node: 0 for node in nodes}
    outgoing = {node: [] for node in nodes}
    for source, target in graph["edges"]:
        if source not in nodes or target not in nodes:
            raise ValueError(f"Unknown graph edge: {source} -> {target}")
        outgoing[source].append(target)
        indegree[target] += 1
    queue = [node for node, degree in indegree.items() if degree == 0]
    visited = []
    while queue:
        node = queue.pop()
        visited.append(node)
        for target in outgoing[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(visited) != len(nodes):
        raise ValueError("Progression graph contains a cycle.")
    return visited


def audit_mandatory_cost_path(root=None):
    balance, costs, graph, buildings = load_data(root)
    validate_graph(graph)
    stock = {key: 0.0 for key in ("metal", "energy", "crystals", "fuel", "credits", "science")}

    def add(bundle):
        for key, amount in bundle.items():
            stock[key] = stock.get(key, 0.0) + float(amount)

    def spend(bundle, label):
        missing = {key: round(float(amount) - stock.get(key, 0.0), 4)
                   for key, amount in bundle.items()
                   if stock.get(key, 0.0) + 1e-8 < float(amount)}
        if missing:
            raise ValueError(f"{label} is resource-blocked: {missing}")
        for key, amount in bundle.items():
            stock[key] -= float(amount)

    add(balance["salvage_reward"])
    spend(buildings["solar_array"]["cost"], "First solar array")
    add(balance["stage_rewards"]["power"]["resources"])
    spend(costs["mining_ship"], "First mining ship")
    spend({"fuel": balance["critical_reserves"]["miner_round_trip_fuel"]}, "Miner round trip")
    add({"metal": balance["production_rates"]["miner"]["cargo_capacity"]})
    add(balance["stage_rewards"]["mining"]["resources"])

    combined = {}
    for building_id in ("smelter", "warehouse"):
        for key, amount in buildings[building_id]["cost"].items():
            combined[key] = combined.get(key, 0.0) + amount
    spend(combined, "Smelter and warehouse")
    add(balance["stage_rewards"]["station"]["resources"])
    spend(buildings["laboratory"]["cost"], "Laboratory")
    spend({"science": 65}, "First research")
    add(balance["stage_rewards"]["science"]["resources"])

    spend(buildings["hangar"]["cost"], "Hangar")
    spend(costs["ships"]["transport"], "Transport ship")
    spend(costs["ships"]["scout"], "Scout ship")
    add(balance["stage_rewards"]["fleet"]["resources"])
    spend({"fuel": balance["critical_reserves"]["first_expedition_fuel"]}, "First expedition")
    add(balance["stage_rewards"]["galaxy"]["resources"])

    spend(costs["ships"]["colonizer"], "First colonizer")
    spend(costs["colonization"], "First colony mission")
    add(balance["stage_rewards"]["colonies"]["resources"])
    spend(costs["ships"]["colonizer"], "Second colonizer")
    spend(costs["colonization"], "Second colony mission")
    return {"remaining": {key: round(value, 4) for key, value in stock.items()},
            "nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
            "path": "PASS"}
