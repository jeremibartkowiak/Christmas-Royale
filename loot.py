from __future__ import annotations

import math

import pygame

from objects import GameObject
from ui import NameTag, ProximityPrompt


class Pickup[T](GameObject):
    """Przedmiot leżący na ziemi (generyk `Pickup[T]`, np. `Pickup[Gun]`).
    Podnoszony przez dotknięcie przez gracza. Nie blokuje ruchu ani strzałów (`collidable=False`)."""

    FRAME_SIZE = 54
    BACK_COLOR = (20, 24, 36, 170)
    BORDER_COLOR = (255, 210, 80)

    def __init__(self, x: float, y: float, item: T, pickup_delay: float = 0.0):
        super().__init__(x, y, self.FRAME_SIZE, self.FRAME_SIZE, (255, 210, 80), collidable=False)
        self.item: T = item
        self.pickup_delay = pickup_delay
        self.time = 0.0
        label = getattr(item, "name", type(item).__name__)
        self.name_tag = NameTag(label)
        self.image = self._build_icon(item)

    def _build_icon(self, item: T) -> pygame.Surface:
        surf = pygame.Surface((self.FRAME_SIZE, self.FRAME_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(surf, self.BACK_COLOR, surf.get_rect(), border_radius=8)
        pygame.draw.rect(surf, self.BORDER_COLOR, surf.get_rect(), width=2, border_radius=8)
        base = getattr(item, "base_image", None)
        if isinstance(base, pygame.Surface):
            max_w = self.FRAME_SIZE - 12
            if base.get_width() > max_w:
                scale = max_w / base.get_width()
                icon = pygame.transform.smoothscale(base, (max_w, max(4, round(base.get_height() * scale))))
            else:
                icon = base
            surf.blit(icon, icon.get_rect(center=(self.FRAME_SIZE // 2, self.FRAME_SIZE // 2)))
        return surf

    @property
    def can_pickup(self) -> bool:
        return self.pickup_delay <= 0

    def update(self, dt: float) -> None:
        self.time += dt
        if self.pickup_delay > 0:
            self.pickup_delay = max(0.0, self.pickup_delay - dt)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        bob = math.sin(self.time * 4.0) * 3
        draw_rect = self.rect.move(-round(camera_offset.x), -round(camera_offset.y) + round(bob))
        surface.blit(self.image, draw_rect)
        self.name_tag.draw(surface, self.rect.move(0, round(bob)), camera_offset)


class Chest[T](GameObject):
    """Skrzynia na mapie przechowująca generyczny przedmiot `T` (np. `Chest[Gun]`).
    Otwierana przez przytrzymanie klawisza `E` w pobliżu (Proximity Prompt)."""

    SIZE = 70
    CLOSED_COLOR = (190, 145, 55)
    OPENED_COLOR = (80, 68, 50)
    HOLD_TIME = 1.0  # sekundy przytrzymania E
    INTERACT_RANGE = 130.0  # zasięg otwierania (px)

    def __init__(self, x: float, y: float, loot: T, hold_time: float = HOLD_TIME,
                 interact_range: float = INTERACT_RANGE, collidable: bool = True):
        super().__init__(x, y, self.SIZE, self.SIZE, self.CLOSED_COLOR, collidable=collidable)
        self.loot: T | None = loot
        self.hold_time = hold_time
        self.interact_range = interact_range
        self.progress = 0.0
        self.opened = False
        self._opener: object | None = None
        self.prompt = ProximityPrompt("E", "Open Chest")

    def in_range(self, player_pos: pygame.Vector2) -> bool:
        return self.pos.distance_to(player_pos) <= self.interact_range

    def update_interaction(self, dt: float, player_pos: pygame.Vector2, holding_interact: bool,
                           actor: object = "player") -> T | None:
        """Aktualizuje otwieranie skrzyni. Po pełnym przytrzymaniu zwraca zawartość `T` i oznacza jako otwartą."""
        if self.opened:
            return None
        if not holding_interact or not self.in_range(player_pos):
            if self._opener is actor:
                self.progress = 0.0
                self._opener = None
            return None
        if self._opener is not None and self._opener is not actor:
            return None  # ktoś inny już otwiera tę skrzynię
        self._opener = actor
        self.progress += dt
        if self.progress >= self.hold_time:
            self.progress = 0.0
            self._opener = None
            self.opened = True
            self.image.fill(self.OPENED_COLOR)
            loot = self.loot
            self.loot = None
            return loot
        return None

    def draw_prompt(self, surface: pygame.Surface, camera_offset: pygame.Vector2,
                    player_pos: pygame.Vector2) -> None:
        if not self.opened and self.in_range(player_pos):
            self.prompt.draw(surface, self.rect, camera_offset, self.progress / self.hold_time)
