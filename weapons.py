from __future__ import annotations

import math
import os
import random
from typing import TYPE_CHECKING

import pygame

from assets import load_image

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
                 points: int = 0, spread_idle: float = 0.0, spread_walk: float = 0.0,
                 spray_pattern: list[float] | None = None, spray_bloom: float = 0.0,
                 max_bloom: float = 5.0, spray_recovery_time: float = 0.35,
                 image_path: str | None = None, icon_path: str | None = None):
        """name: nazwa pokazywana w kill feedzie.
        automatic: True = ogień ciągły po przytrzymaniu LPM, False = jeden strzał na kliknięcie.
        fire_rate: strzały na sekundę. magazine_size: pojemność magazynka. reload_time: sekundy.
        damage: obrażenia zadawane jednym strzałem. length/color: wygląd placeholdera.
        points: punkty w Deathmatchu za zabicie tą bronią.
        spread_idle / spread_walk: bazowy losowy rozrzut (stopnie) w staniu i chodzeniu.
        spray_pattern: lista kątów odchylenia (stopnie, lewo/prawo) dla kolejnych strzałów.
        spray_bloom: przyrost losowego rozrzutu na strzał po pierwszym strzale (do `max_bloom`).
        spray_recovery_time: czas bez strzału (s) resetujący serię i bloom."""
        self.name = name
        self.length = length
        self.damage = damage
        self.points = points
        self.automatic = automatic
        self.fire_rate = fire_rate
        self.magazine_size = magazine_size
        self.reload_time = reload_time
        self.spread_idle = spread_idle
        self.spread_walk = spread_walk
        self.spray_pattern = list(spray_pattern) if spray_pattern else []
        self.spray_bloom = spray_bloom
        self.max_bloom = max_bloom
        self.spray_recovery_time = spray_recovery_time
        self.ammo = magazine_size
        self.reload_left = 0.0  # >0 = trwa przeładowanie
        self.shot_index = 0
        self.since_last_shot = 0.0
        self.current_bloom = 0.0
        self.pos = pygame.Vector2(owner_pos)
        self.direction = pygame.Vector2(1, 0)
        self.angle = 0.0  # stopnie, 0 = w prawo
        # Tekstura .png (rysowana "w prawo") albo fallback na kolorowy prostokąt (greybox)
        tex = load_image(image_path, max_size=(self.length, 64), keep_aspect=True) if image_path else None
        if tex is not None:
            self.base_image = tex
            self.length = tex.get_width()
            self.has_texture = True
        else:
            self.base_image = pygame.Surface((self.length, self.THICKNESS), pygame.SRCALPHA)
            self.base_image.fill(color)
            self.has_texture = False
        self.icon_image = load_image(icon_path, max_size=(52, 52), keep_aspect=True) if icon_path else None
        self.image = self.base_image
        self.cooldown = 0.0

    @property
    def reloading(self) -> bool:
        return self.reload_left > 0

    def reset_spray(self) -> None:
        self.shot_index = 0
        self.current_bloom = 0.0

    def cancel_reload(self) -> None:
        self.reload_left = 0.0

    def set_color(self, color: tuple[int, int, int]) -> None:
        if self.has_texture:
            return
        self.base_image.fill(color)
        self.image = pygame.transform.rotate(self.base_image, self.angle)

    def current_spread(self, move_state: str = "idle") -> float:
        """Aktualny kąt losowego rozrzutu (w stopniach) dla podanego stanu ruchu."""
        base = self.spread_walk if move_state == "walk" else self.spread_idle
        return base + self.current_bloom

    def update(self, dt: float) -> None:
        self.cooldown = max(0.0, self.cooldown - dt)
        self.since_last_shot += dt
        if self.since_last_shot >= self.spray_recovery_time:
            self.shot_index = 0
            if self.spray_recovery_time > 0:
                decay = (self.max_bloom / self.spray_recovery_time) * dt
                self.current_bloom = max(0.0, self.current_bloom - decay)
            else:
                self.current_bloom = 0.0
        if self.reloading:
            self.reload_left -= dt
            if self.reload_left <= 0:
                self.reload_left = 0.0
                self.ammo = self.magazine_size

    def start_reload(self) -> None:
        if not self.reloading and self.ammo < self.magazine_size:
            self.reload_left = self.reload_time
            self.reset_spray()

    def _next_pattern_angle(self) -> float:
        if not self.spray_pattern:
            return 0.0
        idx = min(self.shot_index, len(self.spray_pattern) - 1)
        return self.spray_pattern[idx]

    def fire(self, owner: GameObject, targets: list[GameObject], trigger_held: bool,
             trigger_pressed: bool, move_state: str = "idle", apply_spread: bool = True
             ) -> tuple[Tracer, GameObject | None] | None:
        """Oddaje strzał, jeśli spust jest wciśnięty (zależnie od trybu), jest amunicja, nie trwa
        przeładowanie i minął cooldown. Zwraca (efekt linii, trafiony obiekt) lub None."""
        wants_fire = trigger_held if self.automatic else trigger_pressed
        if not wants_fire or self.reloading or self.ammo <= 0 or self.cooldown > 0:
            return None
        self.ammo -= 1
        self.cooldown = 1.0 / self.fire_rate
        fire_dir = self.direction
        if apply_spread:
            pattern_angle = self._next_pattern_angle()
            spread = self.current_spread(move_state)
            random_offset = random.uniform(-spread, spread) if spread > 0 else 0.0
            fire_dir = self.direction.rotate(pattern_angle + random_offset)
            self.shot_index += 1
            self.since_last_shot = 0.0
            self.current_bloom = min(self.max_bloom, self.current_bloom + self.spray_bloom)
        hit_point, hit_obj = raycast(owner.pos, fire_dir, self.RANGE, targets, ignore=owner)
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
    # Pierwszy strzał celny (0°), kolejne wchodzą w spray pattern (lewo-prawo) i lekki bloom
    pattern = [0.0, -1.5, -3.0, -1.5, 1.5, 3.5, 2.0, -2.0, -4.0, -1.5, 2.5, 4.0]
    return Gun(owner_pos, name="Pistol", automatic=True, fire_rate=6.0, magazine_size=12,
               reload_time=1.5, damage=20, points=16,
               spread_idle=0.0, spread_walk=3.0, spray_pattern=pattern,
               spray_bloom=0.8, max_bloom=4.5, spray_recovery_time=0.35)


def make_sniper(owner_pos: pygame.Vector2) -> Gun:
    # Sniper: 0° w staniu, duży rozrzut podczas chodzenia
    return Gun(owner_pos, name="Sniper", automatic=False, fire_rate=1.0, magazine_size=1,
               reload_time=3.0, damage=100, length=100, color=(120, 140, 120), points=12,
               spread_idle=0.0, spread_walk=8.0, spray_pattern=[], spray_bloom=0.0)


def make_ak47(owner_pos: pygame.Vector2) -> Gun:
    # Tymczasowe statystyki testowe do decyzji Użytkownika
    pattern = [0.0, -1.2, -2.5, -1.0, 1.8, 3.8, 2.5, -1.5, -4.0, -2.0, 2.0, 4.5, 1.5, -2.5]
    return Gun(owner_pos, name="AK-47", automatic=True, fire_rate=9.0, magazine_size=30,
               reload_time=2.0, damage=16, length=112, color=(90, 120, 150), points=14,
               spread_idle=0.0, spread_walk=4.0, spray_pattern=pattern,
               spray_bloom=0.6, max_bloom=5.5, spray_recovery_time=0.4,
               image_path=os.path.join("assets", "weapons", "ak47.png"),
               icon_path=os.path.join("assets", "weapons", "icon_ak47.png"))


make_assault_rifle = make_ak47


# Pula broni do skrzyń (fabryka, waga szansy) - wartości tymczasowe do decyzji Użytkownika
WEAPONS_POOL: list[tuple[callable, float]] = [
    (make_pistol, 55.0),
    (make_ak47, 30.0),
    (make_sniper, 15.0),
]


def roll_weapon(owner_pos: pygame.Vector2) -> Gun:
    """Losuje broń z puli `WEAPONS_POOL` zgodnie z wagami."""
    factories, weights = zip(*WEAPONS_POOL)
    chosen = random.choices(factories, weights=weights, k=1)[0]
    return chosen(owner_pos)


class Inventory:
    """Plecak gracza: lista broni i jedna aktywna. Każda broń trzyma własny stan (amunicję itd.)."""

    def __init__(self, guns: list[Gun]):
        self.guns = guns
        self.index = 0

    @property
    def active(self) -> Gun | None:
        if not self.guns:
            return None
        return self.guns[self.index]

    def add(self, gun: Gun) -> None:
        self.guns.append(gun)
        if len(self.guns) == 1:
            self.index = 0

    def drop_active(self) -> Gun | None:
        """Usuwa aktywną broń z plecaka i ją zwraca (lub None, jeśli plecak jest pusty)."""
        if not self.guns:
            return None
        gun = self.guns.pop(self.index)
        gun.cancel_reload()
        gun.reset_spray()
        if self.guns:
            self.index = min(self.index, len(self.guns) - 1)
        else:
            self.index = 0
        return gun

    def select(self, index: int) -> None:
        if 0 <= index < len(self.guns) and index != self.index:
            if self.active is not None:
                self.active.cancel_reload()  # zmiana broni przerywa przeładowanie
                self.active.reset_spray()
            self.index = index
