from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from settings import VIRTUAL_W, VIRTUAL_H


@dataclass(frozen=True)
class ZonePhase:
    """Pojedyncza faza strefy: czekanie, kurczenie, docelowy promień (ułamek mapy) i obrażenia/s."""
    wait_time: float
    shrink_time: float
    target_ratio: float
    dps: float


# Tymczasowe fazy strefy Battle Royale (do decyzji Użytkownika)
DEFAULT_PHASES: tuple[ZonePhase, ...] = (
    ZonePhase(wait_time=35.0, shrink_time=25.0, target_ratio=0.62, dps=2.0),
    ZonePhase(wait_time=25.0, shrink_time=25.0, target_ratio=0.38, dps=4.0),
    ZonePhase(wait_time=20.0, shrink_time=20.0, target_ratio=0.20, dps=8.0),
    ZonePhase(wait_time=15.0, shrink_time=20.0, target_ratio=0.08, dps=12.0),
    ZonePhase(wait_time=10.0, shrink_time=15.0, target_ratio=0.00, dps=20.0),
)


class StormZone:
    """Fioletowa strefa (Storm) jak w Fortnite: bezpieczne koło, które kurczy się w kolejnych fazach."""

    STORM_COLOR = (135, 45, 205)
    BORDER_COLOR = (195, 95, 255)
    STORM_ALPHA = 115

    def __init__(self, bounds: pygame.Rect, phases: tuple[ZonePhase, ...] = DEFAULT_PHASES):
        self.bounds = bounds
        self.phases = phases
        self.initial_radius = math.hypot(bounds.width, bounds.height) * 0.55
        self.center = pygame.Vector2(bounds.center)
        self.radius = self.initial_radius

        self.phase_index = 0
        self.state = "wait"  # "wait" | "shrink" | "done"
        self.timer = 0.0

        self.start_center = pygame.Vector2(self.center)
        self.start_radius = self.radius
        self.target_center = pygame.Vector2(self.center)
        self.target_radius = self.radius
        self._prepare_next_target()

        # Bufor do rysowania fioletowej strefy poza kołem (bez alokacji co klatkę)
        self._overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H))
        self._overlay.set_colorkey((0, 0, 0))
        self._overlay.set_alpha(self.STORM_ALPHA)

    @property
    def current_phase(self) -> ZonePhase:
        return self.phases[min(self.phase_index, len(self.phases) - 1)]

    @property
    def dps(self) -> float:
        if self.phase_index == 0 and self.state == "wait":
            return 0.0  # przed pierwszym zamknięciem jeszcze nie zadaje obrażeń
        return self.current_phase.dps

    @property
    def time_left(self) -> float:
        if self.state == "done":
            return 0.0
        total = self.current_phase.wait_time if self.state == "wait" else self.current_phase.shrink_time
        return max(0.0, total - self.timer)

    def _prepare_next_target(self) -> None:
        if self.phase_index >= len(self.phases):
            self.state = "done"
            return
        phase = self.phases[self.phase_index]
        self.start_center = pygame.Vector2(self.center)
        self.start_radius = self.radius
        self.target_radius = self.initial_radius * phase.target_ratio
        # Nowy środek zawsze mieści się wewnątrz obecnego koła i granic mapy
        max_shift = max(0.0, self.radius - self.target_radius) * 0.6
        angle = random.uniform(0, 360)
        offset = pygame.Vector2(random.uniform(0, max_shift), 0).rotate(angle)
        candidate = self.center + offset
        margin = self.target_radius * 0.35
        candidate.x = max(self.bounds.left + margin, min(self.bounds.right - margin, candidate.x))
        candidate.y = max(self.bounds.top + margin, min(self.bounds.bottom - margin, candidate.y))
        self.target_center = candidate
        self.state = "wait"
        self.timer = 0.0

    def is_inside(self, pos: pygame.Vector2) -> bool:
        return pos.distance_squared_to(self.center) <= self.radius * self.radius

    def update(self, dt: float) -> None:
        if self.state == "done":
            return
        self.timer += dt
        phase = self.current_phase
        if self.state == "wait":
            if self.timer >= phase.wait_time:
                self.state = "shrink"
                self.timer = 0.0
        elif self.state == "shrink":
            t = min(1.0, self.timer / max(0.01, phase.shrink_time))
            self.center = self.start_center.lerp(self.target_center, t)
            self.radius = self.start_radius + (self.target_radius - self.start_radius) * t
            if t >= 1.0:
                self.phase_index += 1
                self._prepare_next_target()

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        screen_center = (round(self.center.x - camera_offset.x), round(self.center.y - camera_offset.y))
        screen_radius = max(0, round(self.radius))
        self._overlay.fill(self.STORM_COLOR)
        if screen_radius > 0:
            pygame.draw.circle(self._overlay, (0, 0, 0), screen_center, screen_radius)
        surface.blit(self._overlay, (0, 0))
        if screen_radius > 0:
            pygame.draw.circle(surface, self.BORDER_COLOR, screen_center, screen_radius, width=4)
