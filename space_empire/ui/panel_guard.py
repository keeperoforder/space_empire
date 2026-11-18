"""Fault isolation for HUD panels without silently closing the panel.

A transient rendering/input exception must not mutate navigation state. The
panel remains visible and the caller can display a diagnostic overlay.
"""
from __future__ import annotations


class PanelGuard:
    def __init__(self, on_error=None):
        self.on_error = on_error
        self.errors = {}

    def _failed(self, component, exc):
        message = f"{type(exc).__name__}: {exc}"
        previous = self.errors.get(component)
        self.errors[component] = message
        if self.on_error and previous != message:
            self.on_error(component, exc)
        return message

    def handle_event(self, panel, event, component):
        if panel is None or not getattr(panel, "visible", False):
            return False
        try:
            handled = bool(panel.handle_event(event))
            self.errors.pop(component, None)
            return handled
        except Exception as exc:
            self._failed(component, exc)
            # Consume the failing event, but preserve panel visibility and state.
            return True

    def draw(self, panel, surface, component):
        if panel is None or not getattr(panel, "visible", False):
            return False
        try:
            panel.draw(surface)
            self.errors.pop(component, None)
            return True
        except Exception as exc:
            self._failed(component, exc)
            # Crucially, do not set panel.visible=False here.
            return False
