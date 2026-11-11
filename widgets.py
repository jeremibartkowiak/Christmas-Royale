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
