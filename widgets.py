"""Wspólne elementy UI używane w menu, wczytywaniu i menu ESC."""
from __future__ import annotations

import pygame


class Button:
    """Prosty przycisk: prostokąt z napisem, podświetlany po najechaniu myszą."""

    DISABLED_COLOR = (45, 45, 52)
    DISABLED_TEXT_COLOR = (120, 120, 130)

    def __init__(self, rect: pygame.Rect, label: str, font: pygame.font.Font,
                 color: tuple[int, int, int] = (60, 60, 75),
                 hover_color: tuple[int, int, int] = (95, 95, 120),
                 text_color: tuple[int, int, int] = (255, 255, 255),
                 border_radius: int = 8):
        self.rect = rect
        self.label = label
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_radius = border_radius
        self.enabled = True

    def hit(self, pos: pygame.Vector2) -> bool:
        return self.enabled and self.rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface, mouse_pos: pygame.Vector2) -> None:
        if not self.enabled:
            color, text_color = self.DISABLED_COLOR, self.DISABLED_TEXT_COLOR
        else:
            color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
            text_color = self.text_color
        pygame.draw.rect(surface, color, self.rect, border_radius=self.border_radius)
        text = self.font.render(self.label, True, text_color)
        surface.blit(text, text.get_rect(center=self.rect.center))


def draw_placeholder_image(surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int],
                           label: str, font: pygame.font.Font, border_radius: int = 8) -> None:
    """Placeholder obrazka trybu (kolorowy prostokąt z dużą literą) - później podmiana na .png."""
    pygame.draw.rect(surface, color, rect, border_radius=border_radius)
    shade = tuple(max(0, c - 45) for c in color)
    pygame.draw.rect(surface, shade, rect, width=4, border_radius=border_radius)
    text = font.render(label, True, shade)
    surface.blit(text, text.get_rect(center=rect.center))


class Slider:
    """Poziomy suwak UI z etykietą, aktualną wartością i obsługą przeciągania myszą."""

    TRACK_H = 10
    KNOB_RADIUS = 12
    TRACK_COLOR = (45, 52, 72)
    FILL_COLOR = (255, 210, 80)
    KNOB_COLOR = (255, 255, 255)
    KNOB_HOVER_COLOR = (255, 230, 140)
    LABEL_COLOR = (210, 215, 230)
    VALUE_COLOR = (255, 210, 80)

    def __init__(self, rect: pygame.Rect, label: str, min_value: float, max_value: float,
                 step: float, value: float, font: pygame.font.Font, format_value=None):
        self.rect = rect
        self.label = label
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.value = value
        self.font = font
        self.format_value = format_value or (lambda v: f"{v:g}")
        self.dragging = False

    def _track_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.left, self.rect.bottom - 18, self.rect.width, self.TRACK_H)

    def _fraction(self) -> float:
        span = self.max_value - self.min_value
        return (self.value - self.min_value) / span if span > 0 else 0.0

    def _set_from_x(self, x: float) -> None:
        track = self._track_rect()
        t = max(0.0, min(1.0, (x - track.left) / max(1, track.width)))
        raw = self.min_value + t * (self.max_value - self.min_value)
        if self.step > 0:
            raw = self.min_value + round((raw - self.min_value) / self.step) * self.step
        self.value = max(self.min_value, min(self.max_value, raw))

    def handle_event(self, event: pygame.event.Event, mouse_pos: pygame.Vector2) -> bool:
        """Zwraca True, jeśli wartość suwaka mogła się zmienić."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit_area = self._track_rect().inflate(self.KNOB_RADIUS * 2, 24)
            if hit_area.collidepoint(mouse_pos):
                self.dragging = True
                self._set_from_x(mouse_pos.x)
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(mouse_pos.x)
            return True
        return False

    def draw(self, surface: pygame.Surface, mouse_pos: pygame.Vector2) -> None:
        label_surf = self.font.render(self.label, True, self.LABEL_COLOR)
        val_surf = self.font.render(self.format_value(self.value), True, self.VALUE_COLOR)
        surface.blit(label_surf, (self.rect.left, self.rect.top))
        surface.blit(val_surf, val_surf.get_rect(topright=(self.rect.right, self.rect.top)))

        track = self._track_rect()
        pygame.draw.rect(surface, self.TRACK_COLOR, track, border_radius=5)
        fill_w = round(track.width * self._fraction())
        if fill_w > 0:
            pygame.draw.rect(surface, self.FILL_COLOR, pygame.Rect(track.left, track.top, fill_w, track.height),
                             border_radius=5)
        knob_pos = (track.left + fill_w, track.centery)
        hover = pygame.Vector2(knob_pos).distance_to(mouse_pos) <= self.KNOB_RADIUS + 4 or self.dragging
        pygame.draw.circle(surface, self.KNOB_HOVER_COLOR if hover else self.KNOB_COLOR, knob_pos, self.KNOB_RADIUS)
