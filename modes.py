"""Rejestr trybów gry widocznych w menu Play.

Dodanie trybu = jeden wpis w `MODES` (nazwa, opis, kolor/obrazek, zakładka, funkcja tworząca scenę).
Zmiana kolejności na liście = zmiana kolejności wpisów.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

from battle_royale import BattleRoyaleScene
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


DIFFICULTY_LABELS = {1: "Very Easy", 2: "Easy", 3: "Normal", 4: "Hard", 5: "Insane"}


@dataclass(frozen=True)
class ModeOption:
    """Opcja trybu gry wyświetlana jako suwak po wybraniu trybu w menu Play."""
    key: str
    label: str
    min_value: float
    max_value: float
    step: float
    default: float
    format_value: Callable[[float], str] = lambda v: f"{v:g}"


@dataclass(frozen=True)
class GameMode:
    id: str
    name: str
    description: str
    category: str  # id z CATEGORIES
    create_scene: Callable[[App, dict[str, float]], Scene]
    color: tuple[int, int, int] = (90, 90, 110)  # placeholder obrazka (później ścieżka do .png)
    options: tuple[ModeOption, ...] = ()


MODES: list[GameMode] = [
    GameMode(
        id="battle_royale", name="Battle Royale", description="100 players, loot chests, purple storm",
        category="singleplayer", color=(145, 65, 200),
        options=(
            ModeOption("difficulty", "Bot Difficulty", 1, 5, 1, 3,
                       lambda v: DIFFICULTY_LABELS.get(int(v), str(int(v)))),
        ),
        create_scene=lambda app, opts: BattleRoyaleScene(app, opts),
    ),
    GameMode(
        id="deathmatch", name="Deathmatch", description="Up to 16 players (bots)",
        category="singleplayer", color=(70, 130, 200),
        options=(
            ModeOption("difficulty", "Bot Difficulty", 1, 5, 1, 3,
                       lambda v: DIFFICULTY_LABELS.get(int(v), str(int(v)))),
            ModeOption("minutes", "Match Time", 1, 15, 1, 10,
                       lambda v: f"{int(v)} min"),
        ),
        create_scene=lambda app, opts: DeathmatchScene(app, opts),
    ),
    GameMode(id="debug", name="Debug", description="Test arena with bots",
             category="singleplayer", color=(190, 80, 80),
             create_scene=lambda app, _opts: GameScene(app)),
]


def modes_in(category: str) -> list[GameMode]:
    return [m for m in MODES if m.category == category]
