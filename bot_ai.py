"""AI bota do Deathmatchu: porusza się, szuka widocznego przeciwnika i strzela seriami z rozrzutem.
Poziom trudności reguluje się stałymi na górze klasy."""
from __future__ import annotations

import random

import pygame

from entities import Bot
from objects import GameObject, SpawnProtection
from weapons import Inventory, make_pistol, make_sniper, raycast


class AIBot(Bot):
    SPEED = 300  # gracz ma 400
    SIGHT_RANGE = 1100  # w jakiej odległości bot zauważa przeciwnika (musi być widoczny, bez ściany)
    FIRE_RANGE = 800
    PREFERRED_MIN = 250  # bliżej niż to - bot się cofa
    PREFERRED_MAX = 550  # dalej niż to - bot podchodzi
    SNIPER_MIN_RANGE = 520  # powyżej tego dystansu bot preferuje Snipera
    SWITCH_COOLDOWN = 1.2  # min. odstęp między zmianami broni w walce (s)
    STRAFE_WEIGHT = 0.8  # siła ruchu bokiem (uniki)
    REACTION_TIME = 0.45  # s od zauważenia celu do pierwszego strzału
    TURN_SPEED = 220  # stopnie/s - jak szybko bot obraca celownik
    AIM_TOLERANCE = 12  # stopnie - maks. błąd celowania, przy którym bot strzela
    AIM_SPREAD = 7  # stopnie losowego rozrzutu przy każdym strzale
    SNIPER_SPREAD = 9  # większy rozrzut dla Snipera, żeby bot nie zabijał za łatwo na hita
    BURST_SHOTS = (2, 4)  # liczba strzałów w serii (min, max)
    BURST_PAUSE = (0.5, 1.1)  # przerwa między seriami (s)
    THINK_INTERVAL = 0.2  # co ile s bot szuka celu
    STUCK_CHECK = 0.6  # co ile s sprawdza, czy utknął

    def __init__(self, name: str, x: float, y: float, bounds: pygame.Rect, max_hp: float = 100):
        pos = pygame.Vector2(x, y)
        inventory = Inventory([make_pistol(pos), make_sniper(pos)])
        super().__init__(name, x, y, max_hp=max_hp, inventory=inventory)
        self.protection = SpawnProtection()
        self.bounds = bounds  # wnętrze areny - zakres losowania punktów patrolu
        self.target: GameObject | None = None
        self.aim_dir = pygame.Vector2(1, 0).rotate(random.uniform(0, 360))
        self.think_left = random.uniform(0, self.THINK_INTERVAL)
        self.switch_left = 0.0
        self.reaction_left = 0.0
        self.burst_left = 0
        self.pause_left = 0.0
        self.strafe_dir = random.choice((-1, 1))
        self.strafe_left = random.uniform(0.7, 1.6)
        self.wander_point: pygame.Vector2 | None = None
        self.wander_left = 0.0
        self.stuck_left = self.STUCK_CHECK
        self.stuck_ref = pygame.Vector2(x, y)

    def act(self, dt: float, enemies: list[GameObject], obstacles: list[GameObject],
            world: list[GameObject]):
        """Jedna klatka AI. enemies: cele, które bot może atakować; obstacles: tylko przeszkody
        (linia widzenia); world: wszystko, co blokuje ruch i strzały. Zwraca wynik strzału lub None."""
        self.gun.update(dt)
        self.switch_left = max(0.0, self.switch_left - dt)
        self.think_left -= dt
        if self.think_left <= 0:
            self.think_left = self.THINK_INTERVAL
            self._pick_target(enemies, obstacles)
        if self.target is not None and self.target not in enemies:
            self.target = None  # zginął albo dostał ochronę

        move = pygame.Vector2()
        dist = 0.0
        aim_error = 180.0
        if self.target is not None:
            to_target = self.target.pos - self.pos
            dist = to_target.length()
            direction = to_target / dist if dist > 0 else pygame.Vector2(1, 0)
            self.reaction_left = max(0.0, self.reaction_left - dt)
            aim_error = self._turn_toward(direction, self.TURN_SPEED * dt)
            if dist > self.PREFERRED_MAX:
                move += direction
            elif dist < self.PREFERRED_MIN:
                move -= direction
            self.strafe_left -= dt
            if self.strafe_left <= 0:
                self.strafe_dir = -self.strafe_dir
                self.strafe_left = random.uniform(0.7, 1.6)
            move += pygame.Vector2(-direction.y, direction.x) * self.strafe_dir * self.STRAFE_WEIGHT
        else:
            move = self._wander_direction(dt)
            if move.length_squared() > 0:
                self._turn_toward(move, self.TURN_SPEED * dt)

        if move.length_squared() > 0:
            move.normalize_ip()
        self.move_and_collide(move * self.SPEED * dt, world)
        self._check_stuck(dt)

        self._manage_weapon(dist)

        fired = None
        if (self.target is not None and self.reaction_left <= 0 and dist <= self.FIRE_RANGE
                and aim_error <= self.AIM_TOLERANCE):
            fired = self._try_shoot(dt, world)
        else:
            self.pause_left = max(0.0, self.pause_left - dt)
        self.gun.aim_at(self.pos, self.pos + self.aim_dir)  # tylko wygląd (obrót broni)

        if self.protection is not None:
            self.protection.update(dt, move.length_squared() > 0 or fired is not None)
        return fired

    # --- broń i przeładowanie ---
    def _select_weapon(self, index: int) -> None:
        if index != self.inventory.index:
            self.inventory.select(index)
            self.switch_left = self.SWITCH_COOLDOWN
            self.burst_left = 0
            self.pause_left = 0.0

    def _manage_weapon(self, dist: float) -> None:
        """Wybiera broń odpowiednią do dystansu i przeładowuje puste magazynki."""
        if self.target is None:
            if self.gun.reloading:
                return
            if self.gun.ammo < self.gun.magazine_size:
                self.gun.start_reload()
                return
            for i, gun in enumerate(self.inventory.guns):
                if gun.ammo < gun.magazine_size:
                    self._select_weapon(i)
                    self.gun.start_reload()
                    return
            return

        if self.gun.ammo <= 0:
            if not self.gun.reloading:
                for i, gun in enumerate(self.inventory.guns):
                    if gun.ammo > 0:
                        self._select_weapon(i)
                        return
                self.gun.start_reload()
            return

        if self.gun.reloading or self.switch_left > 0:
            return
        preferred = 1 if dist >= self.SNIPER_MIN_RANGE else 0
        if preferred != self.inventory.index and self.inventory.guns[preferred].ammo > 0:
            self._select_weapon(preferred)

    # --- cel i celowanie ---
    def _pick_target(self, enemies: list[GameObject], obstacles: list[GameObject]) -> None:
        """Wybiera najbliższego przeciwnika w zasięgu wzroku, którego nie zasłania ściana."""
        in_range = [e for e in enemies if e.pos.distance_to(self.pos) <= self.SIGHT_RANGE]
        in_range.sort(key=lambda e: e.pos.distance_squared_to(self.pos))
        best = next((e for e in in_range if self._visible(e, obstacles)), None)
        if best is not self.target:
            self.target = best
            self.burst_left = 0
            if best is not None:
                self.reaction_left = self.REACTION_TIME * random.uniform(0.8, 1.3)

    def _visible(self, other: GameObject, obstacles: list[GameObject]) -> bool:
        offset = other.pos - self.pos
        distance = offset.length()
        if distance == 0:
            return True
        _, hit = raycast(self.pos, offset / distance, distance, obstacles)
        return hit is None

    def _turn_toward(self, desired: pygame.Vector2, max_degrees: float) -> float:
        """Obraca celownik w stronę `desired` (ograniczona prędkość). Zwraca pozostały błąd w stopniach."""
        diff = (self.aim_dir.angle_to(desired) + 180) % 360 - 180
        step = max(-max_degrees, min(max_degrees, diff))
        self.aim_dir = self.aim_dir.rotate(step)
        return abs(diff - step)

    def _try_shoot(self, dt: float, world: list[GameObject]):
        """Strzela seriami: kilka strzałów, potem przerwa. Każdy strzał ma losowy rozrzut."""
        self.pause_left = max(0.0, self.pause_left - dt)
        if self.pause_left > 0:
            return None
        if self.burst_left <= 0:
            self.burst_left = random.randint(*self.BURST_SHOTS)
        true_dir = self.gun.direction
        spread = self.SNIPER_SPREAD if self.gun.name == "Sniper" else self.AIM_SPREAD
        self.gun.direction = self.aim_dir.rotate(random.uniform(-spread, spread))
        self.gun.pos = self.pos + self.aim_dir * self.gun.HOLD_DISTANCE
        result = self.gun.fire(self, world, True, True)
        self.gun.direction = true_dir
        if result:
            self.burst_left -= 1
            if self.burst_left <= 0:
                self.pause_left = random.uniform(*self.BURST_PAUSE)
        return result

    # --- ruch ---
    def _wander_direction(self, dt: float) -> pygame.Vector2:
        """Patrol: bot idzie do losowego punktu areny, potem losuje następny."""
        self.wander_left -= dt
        if (self.wander_point is None or self.wander_left <= 0
                or self.pos.distance_to(self.wander_point) < 60):
            self._new_wander_point()
        direction = self.wander_point - self.pos
        return direction.normalize() if direction.length_squared() > 0 else pygame.Vector2()

    def _new_wander_point(self) -> None:
        b = self.bounds
        self.wander_point = pygame.Vector2(random.randint(b.left, b.right), random.randint(b.top, b.bottom))
        self.wander_left = random.uniform(3.0, 6.0)

    def _check_stuck(self, dt: float) -> None:
        """Jeśli bot prawie się nie przesunął (zablokowany przez ścianę), losuje nowy cel patrolu."""
        self.stuck_left -= dt
        if self.stuck_left > 0:
            return
        self.stuck_left = self.STUCK_CHECK
        if self.pos.distance_to(self.stuck_ref) < 20:
            self._new_wander_point()
            self.strafe_dir = -self.strafe_dir
        self.stuck_ref = pygame.Vector2(self.pos)
