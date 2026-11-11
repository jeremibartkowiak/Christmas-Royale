from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from objects import GameObject


def raycast(start: pygame.Vector2, direction: pygame.Vector2, max_range: float,
            targets: list[GameObject], ignore: GameObject | None = None
            ) -> tuple[pygame.Vector2, GameObject | None]:
    """Hitscan: zwraca (punkt trafienia, trafiony obiekt) - najbliższy kolizyjny obiekt na linii.
    Bez trafienia zwraca punkt na końcu zasięgu i None."""
    end = start + direction * max_range
    best_point, best_obj, best_dist = end, None, math.inf
    for obj in targets:
        if obj is ignore or not obj.collidable:
            continue
        clipped = obj.rect.clipline((start.x, start.y), (end.x, end.y))
        if not clipped:
            continue
        point = pygame.Vector2(clipped[0])  # pierwszy punkt = wejście w obiekt (najbliżej strzelca)
        dist = start.distance_squared_to(point)
        if dist < best_dist:
            best_point, best_obj, best_dist = point, obj, dist
    return best_point, best_obj


class Tracer:
    """Chwilowa linia pokazująca tor strzału (efekt prototypowy)."""

    DURATION = 0.08  # sekundy
    COLOR = (255, 230, 80)
    WIDTH = 3

    def __init__(self, start: pygame.Vector2, end: pygame.Vector2):
        self.start = pygame.Vector2(start)
        self.end = pygame.Vector2(end)
        self.age = 0.0

    @property
    def alive(self) -> bool:
        return self.age < self.DURATION

    def update(self, dt: float) -> None:
        self.age += dt

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        pygame.draw.line(surface, self.COLOR, self.start - camera_offset, self.end - camera_offset, self.WIDTH)


class Gun:
    """Prototypowy pistolet (prostokąt) obracany w stronę celu. Strzela hitscanem."""

    THICKNESS = 16
    HOLD_DISTANCE = 45  # odległość środka pistoletu od środka gracza
    RANGE = 2000  # zasięg hitscanu (px)

    def __init__(self, owner_pos: pygame.Vector2, name: str = "Pistol", automatic: bool = True,
                 fire_rate: float = 6.0, magazine_size: int = 12, reload_time: float = 1.5,
                 damage: float = 20, length: int = 60, color: tuple[int, int, int] = (200, 200, 200),
                 points: int = 0):
        """name: nazwa pokazywana w kill feedzie.
        automatic: True = ogień ciągły po przytrzymaniu LPM, False = jeden strzał na kliknięcie.
        fire_rate: strzały na sekundę. magazine_size: pojemność magazynka. reload_time: sekundy.
        damage: obrażenia zadawane jednym strzałem. length/color: wygląd placeholdera.
        points: punkty w Deathmatchu za zabicie tą bronią."""
        self.name = name
        self.length = length
        self.damage = damage
        self.points = points
        self.automatic = automatic
        self.fire_rate = fire_rate
        self.magazine_size = magazine_size
        self.reload_time = reload_time
        self.ammo = magazine_size
        self.reload_left = 0.0  # >0 = trwa przeładowanie
        self.pos = pygame.Vector2(owner_pos)
        self.direction = pygame.Vector2(1, 0)
        self.angle = 0.0  # stopnie, 0 = w prawo
        # Placeholder (greybox) - później podmiana na .png (rysowany "w prawo")
        self.base_image = pygame.Surface((self.length, self.THICKNESS), pygame.SRCALPHA)  # alfa: rogi po obrocie przezroczyste
        self.base_image.fill(color)
        self.image = self.base_image
        self.cooldown = 0.0

    @property
    def reloading(self) -> bool:
        return self.reload_left > 0

    def cancel_reload(self) -> None:
        self.reload_left = 0.0

    def update(self, dt: float) -> None:
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.reloading:
            self.reload_left -= dt
            if self.reload_left <= 0:
                self.reload_left = 0.0
                self.ammo = self.magazine_size

    def start_reload(self) -> None:
        if not self.reloading and self.ammo < self.magazine_size:
            self.reload_left = self.reload_time

    def fire(self, owner: GameObject, targets: list[GameObject], trigger_held: bool,
             trigger_pressed: bool) -> tuple[Tracer, GameObject | None] | None:
        """Oddaje strzał, jeśli spust jest wciśnięty (zależnie od trybu), jest amunicja, nie trwa
        przeładowanie i minął cooldown. Zwraca (efekt linii, trafiony obiekt) lub None."""
        wants_fire = trigger_held if self.automatic else trigger_pressed
        if not wants_fire or self.reloading or self.ammo <= 0 or self.cooldown > 0:
            return None
        self.ammo -= 1
        self.cooldown = 1.0 / self.fire_rate
        hit_point, hit_obj = raycast(owner.pos, self.direction, self.RANGE, targets, ignore=owner)
        muzzle = self.pos + self.direction * (self.length / 2)
        return Tracer(muzzle, hit_point), hit_obj

    def aim_at(self, owner_pos: pygame.Vector2, world_target: pygame.Vector2) -> None:
        to_target = world_target - owner_pos
        if to_target.length_squared() > 0:
            self.direction = to_target.normalize()
            # oś Y ekranu rośnie w dół, stąd minus przy obrocie
            self.angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
        self.pos = owner_pos + self.direction * self.HOLD_DISTANCE
        self.image = pygame.transform.rotate(self.base_image, self.angle)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        center = (round(self.pos.x - camera_offset.x), round(self.pos.y - camera_offset.y))
        surface.blit(self.image, self.image.get_rect(center=center))


def make_pistol(owner_pos: pygame.Vector2) -> Gun:
    return Gun(owner_pos, name="Pistol", automatic=True, fire_rate=6.0, magazine_size=12,
               reload_time=1.5, damage=20, points=16)


def make_sniper(owner_pos: pygame.Vector2) -> Gun:
    return Gun(owner_pos, name="Sniper", automatic=False, fire_rate=1.0, magazine_size=1,
               reload_time=3.0, damage=100, length=100, color=(120, 140, 120), points=12)


class Inventory:
    """Plecak gracza: lista broni i jedna aktywna. Każda broń trzyma własny stan (amunicję itd.)."""

    def __init__(self, guns: list[Gun]):
        self.guns = guns
        self.index = 0

    @property
    def active(self) -> Gun:
        return self.guns[self.index]

    def select(self, index: int) -> None:
        if 0 <= index < len(self.guns) and index != self.index:
            self.active.cancel_reload()  # zmiana broni przerywa przeładowanie
            self.index = index
