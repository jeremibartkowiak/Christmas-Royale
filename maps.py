"""Mapy aren: obstacle'e, punkty spawnu i granice. Docelowo mogą być wczytywane z pliku."""
from __future__ import annotations

import random
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


def make_br_arena(chest_count: int = 90) -> tuple[ArenaMap, list[tuple[int, int]]]:
    """Wielka mapa Battle Royale (8000x8000) z losowymi osłonami, skrzyniami i punktami spawnu."""
    bounds = pygame.Rect(-4000, -4000, 8000, 8000)
    crate = (120, 90, 60)
    wall = (110, 110, 120)
    obstacles: list[tuple] = []
    obstacle_rects: list[pygame.Rect] = []

    def try_add_obstacle(cx: int, cy: int, w: int, h: int, color: tuple[int, int, int]) -> bool:
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (cx, cy)
        padded = rect.inflate(140, 140)
        if not bounds.inflate(-260, -260).contains(rect):
            return False
        if any(padded.colliderect(r) for r in obstacle_rects):
            return False
        obstacles.append((cx, cy, w, h, color))
        obstacle_rects.append(rect)
        return True

    # Rozrzucone ściany i skrzynie tworzące osłony na całej mapie
    for _ in range(160):
        cx = random.randint(bounds.left + 250, bounds.right - 250)
        cy = random.randint(bounds.top + 250, bounds.bottom - 250)
        kind = random.choice(("crate", "wall_h", "wall_v"))
        if kind == "crate":
            size = random.choice((120, 160))
            try_add_obstacle(cx, cy, size, size, crate)
        elif kind == "wall_h":
            try_add_obstacle(cx, cy, random.choice((280, 420)), 44, wall)
        else:
            try_add_obstacle(cx, cy, 44, random.choice((280, 420)), wall)

    def free_point(margin: int = 180) -> tuple[int, int]:
        for _ in range(50):
            px = random.randint(bounds.left + margin, bounds.right - margin)
            py = random.randint(bounds.top + margin, bounds.bottom - margin)
            probe = pygame.Rect(0, 0, 90, 90)
            probe.center = (px, py)
            if not any(probe.colliderect(r) for r in obstacle_rects):
                return (px, py)
        return (0, 0)

    chest_spots = [free_point(240) for _ in range(chest_count)]
    spawns = [free_point(200) for _ in range(140)]
    return ArenaMap("Christmas Island", bounds, obstacles, spawns), chest_spots
