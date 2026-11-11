from __future__ import annotations

import pygame

from modes import GameMode
from scene import Scene
from settings import VIRTUAL_W, VIRTUAL_H
from widgets import draw_placeholder_image


class LoadingScene(Scene):
    """Stylistyczny ekran wczytywania: obrazek trybu, nazwa, animowany napis i pasek postępu.
    Po `LOAD_TIME` sekundach tworzy scenę wybranego trybu (wczytanie jest w praktyce natychmiastowe,
    więc czas jest sztuczny - docelowo tu będzie ładowanie tekstur i mapy)."""

    LOAD_TIME = 1.8
    BG_COLOR = (14, 17, 27)
    ACCENT = (255, 210, 80)
    IMAGE_SIZE = (720, 405)
    BAR_SIZE = (900, 14)

    def __init__(self, app, mode: GameMode):
        super().__init__(app)
        self.mode = mode
        self.time = 0.0
        self.label_font = pygame.font.Font(None, 54)
        self.label_font.set_bold(True)
        self.name_font = pygame.font.Font(None, 90)
        self.name_font.set_bold(True)
        self.letter_font = pygame.font.Font(None, 300)

    @property
    def progress(self) -> float:
        t = min(1.0, self.time / self.LOAD_TIME)
        return t * t * (3 - 2 * t)  # smoothstep: płynny start i koniec

    def update(self, dt: float) -> None:
        self.time += dt
        if self.time >= self.LOAD_TIME:
            self.app.change_scene(self.mode.create_scene(self.app))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(self.BG_COLOR)
        image_rect = pygame.Rect(0, 0, *self.IMAGE_SIZE)
        image_rect.center = (VIRTUAL_W // 2, VIRTUAL_H // 2 - 70)
        draw_placeholder_image(surface, image_rect, self.mode.color, self.mode.name[:1].upper(),
                               self.letter_font, border_radius=16)
        name = self.name_font.render(self.mode.name.upper(), True, (255, 255, 255))
        surface.blit(name, name.get_rect(midtop=(VIRTUAL_W // 2, image_rect.bottom + 30)))
        dots = "." * (int(self.time * 3) % 4)
        label = self.label_font.render("LOADING" + dots, True, (190, 195, 210))
        surface.blit(label, label.get_rect(topleft=(VIRTUAL_W // 2 - self.BAR_SIZE[0] // 2, VIRTUAL_H - 150)))
        bar = pygame.Rect(0, 0, *self.BAR_SIZE)
        bar.midtop = (VIRTUAL_W // 2, VIRTUAL_H - 90)
        pygame.draw.rect(surface, (40, 45, 62), bar, border_radius=7)
        fill = bar.copy()
        fill.width = max(1, round(bar.width * self.progress))
        pygame.draw.rect(surface, self.ACCENT, fill, border_radius=7)
