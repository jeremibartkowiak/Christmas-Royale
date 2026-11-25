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


def _house_spec(cx: int, cy: int) -> tuple[list[tuple], list[tuple[int, int]], pygame.Rect]:
    """Domek 440x340 z dwoma wejściami i 2 skrzyniami w środku."""
    w, h, t = 440, 340, 36
    wall = (115, 118, 130)
    crate = (120, 90, 60)
    obs = [
        (cx - 125, cy - h // 2, 190, t, wall),  # góra lewa + przerwa na drzwi
        (cx + 125, cy - h // 2, 190, t, wall),  # góra prawa
        (cx - 125, cy + h // 2, 190, t, wall),  # dół lewa
        (cx + 125, cy + h // 2, 190, t, wall),  # dół prawa
        (cx - w // 2, cy, t, h + t, wall),  # lewa ściana
        (cx + w // 2, cy, t, h + t, wall),  # prawa ściana
        (cx, cy, 80, 80, crate),  # stół/skrzynia w środku
    ]
    chests = [(cx - 130, cy - 85), (cx + 130, cy + 85)]
    bounds = pygame.Rect(cx - w // 2 - 40, cy - h // 2 - 40, w + 80, h + 80)
    return obs, chests, bounds


def _warehouse_spec(cx: int, cy: int) -> tuple[list[tuple], list[tuple[int, int]], pygame.Rect]:
    """Duży magazyn 640x460 z szerokimi wjazdami i 3 skrzyniami."""
    w, h, t = 640, 460, 40
    wall = (95, 105, 120)
    crate = (120, 90, 60)
    obs = [
        (cx, cy - h // 2, w + t, t, wall),  # pełna góra
        (cx, cy + h // 2, w + t, t, wall),  # pełny dół
        (cx - w // 2, cy - 150, t, 160, wall),  # lewa góra (brama pośrodku)
        (cx - w // 2, cy + 150, t, 160, wall),  # lewy dół
        (cx + w // 2, cy - 150, t, 160, wall),  # prawa góra (brama pośrodku)
        (cx + w // 2, cy + 150, t, 160, wall),  # prawy dół
        (cx - 120, cy - 80, 90, 90, crate),
        (cx + 120, cy + 80, 90, 90, crate),
    ]
    chests = [(cx - 220, cy - 140), (cx + 220, cy - 140), (cx, cy + 140)]
    bounds = pygame.Rect(cx - w // 2 - 50, cy - h // 2 - 50, w + 100, h + 100)
    return obs, chests, bounds


def _outpost_spec(cx: int, cy: int) -> tuple[list[tuple], list[tuple[int, int]], pygame.Rect]:
    """Otwarty posterunek z 4 narożnymi murkami i 2 skrzyniami."""
    wall = (110, 110, 120)
    obs = [
        (cx - 150, cy - 150, 140, 36, wall), (cx - 202, cy - 98, 36, 140, wall),
        (cx + 150, cy - 150, 140, 36, wall), (cx + 202, cy - 98, 36, 140, wall),
        (cx - 150, cy + 150, 140, 36, wall), (cx - 202, cy + 98, 36, 140, wall),
        (cx + 150, cy + 150, 140, 36, wall), (cx + 202, cy + 98, 36, 140, wall),
    ]
    chests = [(cx - 75, cy), (cx + 75, cy)]
    bounds = pygame.Rect(cx - 260, cy - 220, 520, 440)
    return obs, chests, bounds


def make_br_arena() -> tuple[ArenaMap, list[tuple[int, int]]]:
    """Wielka mapa Battle Royale (16000x16000) ze strukturami (domki, magazyny, posterunki).
    Skrzynie stoją wyłącznie w strukturach, a między nimi znajdują się drobne osłony."""
    bounds = pygame.Rect(-8000, -8000, 16000, 16000)
    crate = (120, 90, 60)
    obstacles: list[tuple] = []
    obstacle_rects: list[pygame.Rect] = []
    structure_rects: list[pygame.Rect] = []
    chest_spots: list[tuple[int, int]] = []

    def add_obs(spec: tuple) -> None:
        cx, cy, w, h = spec[0], spec[1], spec[2], spec[3]
        r = pygame.Rect(0, 0, w, h)
        r.center = (cx, cy)
        obstacles.append(spec)
        obstacle_rects.append(r)

    # 1. Rozmieszczamy ~32 struktury na całej mapie (z odstępem między sobą)
    builders = (_house_spec, _warehouse_spec, _outpost_spec)
    for _ in range(260):
        if len(structure_rects) >= 32:
            break
        cx = random.randint(bounds.left + 900, bounds.right - 900)
        cy = random.randint(bounds.top + 900, bounds.bottom - 900)
        obs_list, chests, s_rect = random.choice(builders)(cx, cy)
        padded = s_rect.inflate(450, 450)
        if any(padded.colliderect(other) for other in structure_rects):
            continue
        structure_rects.append(s_rect)
        for spec in obs_list:
            add_obs(spec)
        chest_spots.extend(chests)

    # 2. Drobne osłony terenowe (skrzynki/kamienie) poza strukturami
    for _ in range(180):
        cx = random.randint(bounds.left + 400, bounds.right - 400)
        cy = random.randint(bounds.top + 400, bounds.bottom - 400)
        size = random.choice((100, 130))
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (cx, cy)
        padded = rect.inflate(160, 160)
        if any(padded.colliderect(r) for r in structure_rects) or any(padded.colliderect(r) for r in obstacle_rects):
            continue
        add_obs((cx, cy, size, size, crate))

    def free_point(margin: int = 350) -> tuple[int, int]:
        for _ in range(80):
            px = random.randint(bounds.left + margin, bounds.right - margin)
            py = random.randint(bounds.top + margin, bounds.bottom - margin)
            probe = pygame.Rect(0, 0, 90, 90)
            probe.center = (px, py)
            if not any(probe.colliderect(r) for r in obstacle_rects):
                return (px, py)
        return (0, 0)

    spawns = [free_point() for _ in range(150)]
    return ArenaMap("Christmas Island", bounds, obstacles, spawns), chest_spots
