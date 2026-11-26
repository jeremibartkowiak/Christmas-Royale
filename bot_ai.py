"""AI bota do Deathmatchu: porusza się, szuka widocznego przeciwnika i strzela seriami z rozrzutem.
Poziom trudności reguluje się stałymi na górze klasy."""
from __future__ import annotations

import random

import pygame

from entities import Bot
from objects import GameObject, SpawnProtection
from weapons import Inventory, make_pistol, make_sniper, raycast


# Poziomy trudności botów (1 = Very Easy ... 5 = Insane; 3 = domyślny Normal)
DIFFICULTY_PRESETS: dict[int, dict] = {
    1: {"speed": 210, "sight_range": 750, "reaction_time": 1.10, "turn_speed": 100,
        "aim_tolerance": 22, "aim_spread": 15, "sniper_spread": 20, "burst_shots": (1, 2), "burst_pause": (1.2, 2.2)},
    2: {"speed": 255, "sight_range": 900, "reaction_time": 0.75, "turn_speed": 150,
        "aim_tolerance": 16, "aim_spread": 11, "sniper_spread": 14, "burst_shots": (1, 3), "burst_pause": (0.8, 1.6)},
    3: {"speed": 300, "sight_range": 1100, "reaction_time": 0.45, "turn_speed": 220,
        "aim_tolerance": 12, "aim_spread": 7, "sniper_spread": 9, "burst_shots": (2, 4), "burst_pause": (0.5, 1.1)},
    4: {"speed": 345, "sight_range": 1250, "reaction_time": 0.30, "turn_speed": 300,
        "aim_tolerance": 9, "aim_spread": 4.5, "sniper_spread": 6, "burst_shots": (2, 5), "burst_pause": (0.35, 0.8)},
    5: {"speed": 385, "sight_range": 1400, "reaction_time": 0.18, "turn_speed": 380,
        "aim_tolerance": 6, "aim_spread": 2.5, "sniper_spread": 3.5, "burst_shots": (3, 5), "burst_pause": (0.25, 0.55)},
}


class AIBot(Bot):
    FIRE_RANGE = 800
    PREFERRED_MIN = 250  # bliżej niż to - bot się cofa
    PREFERRED_MAX = 550  # dalej niż to - bot podchodzi
    SNIPER_MIN_RANGE = 520  # powyżej tego dystansu bot preferuje Snipera
    SWITCH_COOLDOWN = 1.2  # min. odstęp między zmianami broni w walce (s)
    STRAFE_WEIGHT = 0.8  # siła ruchu bokiem (uniki)
    THINK_INTERVAL = 0.2  # co ile s bot szuka celu
    STUCK_CHECK = 0.6  # co ile s sprawdza, czy utknął

    def __init__(self, name: str, x: float, y: float, bounds: pygame.Rect, max_hp: float = 100,
                 difficulty: int = 3, start_empty: bool = False):
        pos = pygame.Vector2(x, y)
        guns = [] if start_empty else [make_pistol(pos), make_sniper(pos)]
        inventory = Inventory(guns)
        super().__init__(name, x, y, max_hp=max_hp, inventory=inventory)
        preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS[3])
        self.speed: float = preset["speed"]
        self.sight_range: float = preset["sight_range"]
        self.reaction_time: float = preset["reaction_time"]
        self.turn_speed: float = preset["turn_speed"]
        self.aim_tolerance: float = preset["aim_tolerance"]
        self.aim_spread: float = preset["aim_spread"]
        self.sniper_spread: float = preset["sniper_spread"]
        self.burst_shots: tuple[int, int] = preset["burst_shots"]
        self.burst_pause: tuple[float, float] = preset["burst_pause"]
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
        self.unstuck_left = 0.0
        self.stuck_left = self.STUCK_CHECK
        self.stuck_ref = pygame.Vector2(x, y)

    def act(self, dt: float, enemies: list[GameObject], obstacles: list[GameObject],
            world: list[GameObject], safe_center: pygame.Vector2 | None = None,
            safe_radius: float | None = None, loot_target: pygame.Vector2 | None = None,
            opening_chest: bool = False):
        """Jedna klatka AI. enemies: cele, które bot może atakować; obstacles: tylko przeszkody
        (linia widzenia); world: wszystko, co blokuje ruch i strzały. Zwraca wynik strzału lub None."""
        gun = self.gun
        if gun is not None:
            gun.update(dt)
        self.switch_left = max(0.0, self.switch_left - dt)
        self.think_left -= dt
        if self.think_left <= 0:
            self.think_left = self.THINK_INTERVAL
            if gun is not None:
                self._pick_target(enemies, obstacles)
            else:
                self.target = None
        if self.target is not None and self.target not in enemies:
            self.target = None  # zginął albo dostał ochronę

        move = pygame.Vector2()
        dist = 0.0
        aim_error = 180.0
        outside_storm = (safe_center is not None and safe_radius is not None
                         and self.pos.distance_to(safe_center) > safe_radius * 0.9)
        self.unstuck_left = max(0.0, self.unstuck_left - dt)

        if gun is None:
            if opening_chest:
                move = pygame.Vector2()
            elif self.unstuck_left > 0:
                move = self._wander_direction(dt)
            elif loot_target is not None and not outside_storm:
                to_loot = loot_target - self.pos
                move = to_loot.normalize() if to_loot.length_squared() > 0 else pygame.Vector2()
            elif outside_storm and safe_center is not None:
                to_safe = safe_center - self.pos
                move = to_safe.normalize() if to_safe.length_squared() > 0 else pygame.Vector2()
            else:
                move = self._wander_direction(dt)
            if move.length_squared() > 0:
                self._turn_toward(move, self.turn_speed * dt)
        elif outside_storm and safe_center is not None and self.target is None:
            to_safe = safe_center - self.pos
            move = to_safe.normalize() if to_safe.length_squared() > 0 else pygame.Vector2()
            if move.length_squared() > 0:
                self._turn_toward(move, self.turn_speed * dt)
        elif self.target is not None:
            to_target = self.target.pos - self.pos
            dist = to_target.length()
            direction = to_target / dist if dist > 0 else pygame.Vector2(1, 0)
            self.reaction_left = max(0.0, self.reaction_left - dt)
            aim_error = self._turn_toward(direction, self.turn_speed * dt)
            if dist > self.PREFERRED_MAX:
                move += direction
            elif dist < self.PREFERRED_MIN:
                move -= direction
            self.strafe_left -= dt
            if self.strafe_left <= 0:
                self.strafe_dir = -self.strafe_dir
                self.strafe_left = random.uniform(0.7, 1.6)
            move += pygame.Vector2(-direction.y, direction.x) * self.strafe_dir * self.STRAFE_WEIGHT
            if outside_storm and safe_center is not None:
                to_safe = safe_center - self.pos
                if to_safe.length_squared() > 0:
                    move += to_safe.normalize() * 1.2
        else:
            move = self._wander_direction(dt)
            if move.length_squared() > 0:
                self._turn_toward(move, self.turn_speed * dt)

        if move.length_squared() > 0:
            move.normalize_ip()
        self.move_and_collide(move * self.speed * dt, world)
        if opening_chest:
            self.stuck_left = self.STUCK_CHECK
            self.stuck_ref = pygame.Vector2(self.pos)
        else:
            self._check_stuck(dt)

        if gun is not None:
            self._manage_weapon(dist)

        fired = None
        if (gun is not None and self.target is not None and self.reaction_left <= 0
                and dist <= self.FIRE_RANGE and aim_error <= self.aim_tolerance):
            fired = self._try_shoot(dt, world)
        else:
            self.pause_left = max(0.0, self.pause_left - dt)
        if self.gun is not None:
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
        # Gdy wszystkie bronie są w normie, dobierz najlepszą wg dystansu (jeśli ma więcej niż 1)
        if len(self.inventory.guns) < 2:
            return
        preferred = 1 if (self.inventory.guns[1].name in ("AWP", "Sniper") and dist >= self.SNIPER_MIN_RANGE) else 0
        if preferred != self.inventory.index and self.inventory.guns[preferred].ammo > 0:
            self._select_weapon(preferred)

    # --- cel i celowanie ---
    def _pick_target(self, enemies: list[GameObject], obstacles: list[GameObject]) -> None:
        """Wybiera najbliższego przeciwnika w zasięgu wzroku, którego nie zasłania ściana."""
        in_range = [e for e in enemies if e.pos.distance_to(self.pos) <= self.sight_range]
        in_range.sort(key=lambda e: e.pos.distance_squared_to(self.pos))
        best = next((e for e in in_range if self._visible(e, obstacles)), None)
        if best is not self.target:
            self.target = best
            self.burst_left = 0
            if best is not None:
                self.reaction_left = self.reaction_time * random.uniform(0.8, 1.3)

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
            self.burst_left = random.randint(*self.burst_shots)
        true_dir = self.gun.direction
        spread = self.sniper_spread if self.gun.name in ("AWP", "Sniper") else self.aim_spread
        self.gun.direction = self.aim_dir.rotate(random.uniform(-spread, spread))
        self.gun.pos = self.pos + self.aim_dir * self.gun.HOLD_DISTANCE
        result = self.gun.fire(self, world, True, True, apply_spread=False)
        self.gun.direction = true_dir
        if result:
            self.burst_left -= 1
            if self.burst_left <= 0:
                self.pause_left = random.uniform(*self.burst_pause)
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
            self.unstuck_left = 1.4  # chwilowe obejście ściany zamiast pchania się w mur
        self.stuck_ref = pygame.Vector2(self.pos)
