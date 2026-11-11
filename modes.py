"""Rejestr trybów gry widocznych w menu Play.

Dodanie trybu = jeden wpis w `MODES` (nazwa, opis, kolor/obrazek, zakładka, funkcja tworząca scenę).
Zmiana kolejności na liście = zmiana kolejności wpisów.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

from deathmatch import DeathmatchScene
from game import GameScene

if TYPE_CHECKING:
    from app import App
    from scene import Scene

# Zakładki w menu Play: (id, napis). Kolejność = kolejność zakładek.
CATEGORIES: list[tuple[str, str]] = [
    ("multiplayer", "MULTIPLAYER"),
    ("singleplayer", "SINGLEPLAYER"),
]


@dataclass(frozen=True)
class GameMode:
    id: str
    name: str
    description: str
    category: str  # id z CATEGORIES
    create_scene: Callable[[App], Scene]
    color: tuple[int, int, int] = (90, 90, 110)  # placeholder obrazka (później ścieżka do .png)


MODES: list[GameMode] = [
    GameMode(id="deathmatch", name="Deathmatch", description="10 min, up to 16 players (bots)",
             category="singleplayer", color=(70, 130, 200),
             create_scene=lambda app: DeathmatchScene(app)),
    GameMode(id="debug", name="Debug", description="Test arena with bots",
             category="singleplayer", color=(190, 80, 80),
             create_scene=lambda app: GameScene(app)),
]


def modes_in(category: str) -> list[GameMode]:
    return [m for m in MODES if m.category == category]
