from __future__ import annotations

import math

import pygame


class Health:
    """Komponent punktów życia - wielokrotnego użytku (gracz, boty, niszczalne obiekty na mapie)."""

    def __init__(self, max_hp: float):
        self.max_hp = max_hp
        self.hp = max_hp

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    @property
    def fraction(self) -> float:
        return self.hp / self.max_hp

    def take_damage(self, amount: float) -> None:
        self.hp = max(0, self.hp - amount)

    def heal(self, amount: float) -> None:
        self.hp = min(self.max_hp, self.hp + amount)


class SpawnProtection:
    """Ochrona po odrodzeniu: obowiązkowa przez `min_time` s, potem znika, gdy właściciel próbuje
    się ruszać lub strzelać (`acted`), a najpóźniej po `max_time` s."""

    MIN_TIME = 2.0
    MAX_TIME = 5.0

    def __init__(self, min_time: float = MIN_TIME, max_time: float = MAX_TIME):
        self.min_time = min_time
        self.max_time = max_time
        self.elapsed = 0.0
        self.active = True

    def update(self, dt: float, acted: bool) -> None:
        if not self.active:
            return
        self.elapsed += dt
        if self.elapsed >= self.max_time or (self.elapsed >= self.min_time and acted):
            self.active = False


class GameObject:
    """Bazowy obiekt świata (greybox). Kolizje włącza się flagą `collidable` w konstruktorze,
    a punkty życia podaniem `max_hp` (None = obiekt niezniszczalny)."""

    MAX_STEP = 8  # maks. przesunięcie (px) w jednym kroku kolizji
    PROTECTION_COLOR = (120, 220, 255)

    def __init__(self, x: float, y: float, width: int, height: int, color: tuple[int, int, int],
                 collidable: bool = True, max_hp: float | None = None):
        self.pos = pygame.Vector2(x, y)  # środek obiektu
        self.collidable = collidable
        self.name = ""  # pusta = obiekt bez nazwy (nie trafia do kill feedu)
        self.health: Health | None = Health(max_hp) if max_hp is not None else None
        self.protection: SpawnProtection | None = None  # ochrona po spawnie (None = brak)
        # Placeholder (greybox) - później podmiana na .png
        self.image = pygame.Surface((width, height))
        self.image.fill(color)

    @property
    def rect(self) -> pygame.Rect:
        return self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def move_and_collide(self, delta: pygame.Vector2, solids: list[GameObject]) -> None:
        """Przesuwa obiekt osobno w osi X i Y i cofa go przy zderzeniu z kolizyjnymi obiektami
        (dzięki temu obiekt ślizga się wzdłuż ścian). Ta sama metoda posłuży pociskom.
        Ruch jest dzielony na małe kroki, żeby szybki obiekt nie przeskoczył przez cienką ścianę."""
        steps = max(1, math.ceil(max(abs(delta.x), abs(delta.y)) / self.MAX_STEP))
        step = delta / steps
        for _ in range(steps):
            self._step_and_collide(step, solids)

    def _step_and_collide(self, delta: pygame.Vector2, solids: list[GameObject]) -> None:
        for axis in (0, 1):
            self.pos[axis] += delta[axis]
            if not self.collidable:
                continue
            for other in solids:
                if other is self or not other.collidable:
                    continue
                mine, theirs = self.rect, other.rect
                if not mine.colliderect(theirs):
                    continue
                half = (mine.width if axis == 0 else mine.height) / 2
                if axis == 0:
                    self.pos.x = theirs.left - half if delta.x > 0 else theirs.right + half
                else:
                    self.pos.y = theirs.top - half if delta.y > 0 else theirs.bottom + half

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        surface.blit(self.image, self.rect.move(-round(camera_offset.x), -round(camera_offset.y)))
        if self.protection is not None and self.protection.active:
            ring = self.rect.inflate(18, 18).move(-round(camera_offset.x), -round(camera_offset.y))
            pygame.draw.rect(surface, self.PROTECTION_COLOR, ring, width=3, border_radius=8)


class Obstacle(GameObject):
    """Przeszkoda statyczna: ściana, skała itp. (domyślnie z kolizją)."""

    def __init__(self, x: float, y: float, width: int, height: int,
                 color: tuple[int, int, int] = (110, 110, 120), collidable: bool = True,
                 max_hp: float | None = None):
        super().__init__(x, y, width, height, color, collidable, max_hp)
