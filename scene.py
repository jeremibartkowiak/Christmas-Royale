from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from app import App


class Scene:
    """Baza ekranu gry (menu, wczytywanie, mecz...). `App` woła te metody co klatkę
    na aktywnej scenie. Zmiana sceny: `app.change_scene(...)`."""

    def __init__(self, app: App):
        self.app = app

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass
