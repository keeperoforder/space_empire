"""Resolve construction availability from progression state without soft-locking UI."""
from __future__ import annotations


def allowed_building_ids(progression, available_ids):
    """Return buildable IDs for the best-supported current tutorial stage.

    Saved games from earlier versions may contain a stale stage_id while
    stage_index/active_task_id already point at the next task. Prefer the
    active task, then a consistent stage index, and only then stage_id.
    """
    available = set(available_ids)
    if progression is None:
        return available

    configured = getattr(progression, "balance", {}).get(
        "available_buildings_by_stage", {}
    )
    if not isinstance(configured, dict) or not configured:
        # Missing balance data must not make the entire constructor disappear.
        return available

    stage_id = getattr(progression, "stage_id", None)
    active_task_id = getattr(progression, "active_task_id", None)
    stages = getattr(progression, "stages", ())
    stage_index = getattr(progression, "stage_index", None)

    # A completed/legacy campaign has no tutorial construction restriction.
    if stage_id in ("empire_established", "legacy_campaign"):
        return available

    candidates = []
    if isinstance(stage_index, int) and 0 <= stage_index < len(stages):
        indexed_id = stages[stage_index].get("id")
        if indexed_id:
            candidates.append(indexed_id)
    if active_task_id:
        candidates.append(active_task_id)
    if stage_id:
        candidates.append(stage_id)

    resolved = next((candidate for candidate in candidates if candidate in configured), None)
    if resolved is None:
        # Unknown/corrupt state is kept at the safest tutorial gate, not all-open.
        resolved = "awakening" if "awakening" in configured else None
    if resolved is None:
        return available

    return available.intersection(configured.get(resolved, ()))
