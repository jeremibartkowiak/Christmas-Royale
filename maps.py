"""Mapy aren: obstacle'e, punkty spawnu i granice. Docelowo mogą być wczytywane z pliku."""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from objects import Obstacle


@dataclass
class ArenaMap:
    name: str
    bounds: pygame.Rect  # wnętrze areny (granica ścian)
    obstacles: list[tuple]  # (x, y, szerokość, wysokość[, kolor]) - środek obiektu
    spawn_points: list[tuple[int, int]]
    wall_thickness: int = 60

    def build_obstacles(self) -> list[Obstacle]:
        """Zamknięta arena: cztery ściany dookoła + przeszkody w środku."""
        b, t = self.bounds, self.wall_thickness
        walls = [
            Obstacle(b.centerx, b.top - t // 2, b.width + 2 * t, t),
            Obstacle(b.centerx, b.bottom + t // 2, b.width + 2 * t, t),
            Obstacle(b.left - t // 2, b.centery, t, b.height),
            Obstacle(b.right + t // 2, b.centery, t, b.height),
        ]
        return walls + [Obstacle(*spec) for spec in self.obstacles]


def make_dm_arena() -> ArenaMap:
    """Prosta zamknięta arena (3200x2000) pod maks. 16 graczy: symetryczne osłony i 16 punktów spawnu."""
    crate = (120, 90, 60)
    obstacles = [
        (0, 0, 140, 140, crate),  # środek
        (-500, -300, 120, 120), (500, -300, 120, 120),  # filary
        (-500, 300, 120, 120), (500, 300, 120, 120),
        (0, -500, 500, 40), (0, 500, 500, 40),  # długie ściany
        (-1000, 0, 40, 400), (1000, 0, 40, 400),
        (-1300, -600, 160, 160, crate), (1300, -600, 160, 160, crate),  # skrzynie w rogach
        (-1300, 600, 160, 160, crate), (1300, 600, 160, 160, crate),
    ]
    spawns = [(x, y) for x in (-1450, -800, 800, 1450) for y in (-850, -300, 300, 850)]
    return ArenaMap("Deathmatch Arena", pygame.Rect(-1600, -1000, 3200, 2000), obstacles, spawns)
