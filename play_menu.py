from __future__ import annotations

import pygame

from modes import CATEGORIES, GameMode, modes_in
from settings import VIRTUAL_W, VIRTUAL_H
from widgets import Button, draw_placeholder_image


class PlayCard:
    """Karta wyboru trybu (zakrywa lobby pod górnym paskiem): zakładki kategorii, kafelki trybów
    z listy `MODES` i zielony przycisk Join. Zwraca "close" z `handle_event` po wyjściu."""

    BG_COLOR = (18, 22, 34)
    ACCENT = (255, 210, 80)
    MARGIN_X = 120
    TAB_SIZE = (320, 64)
    TAB_GAP = 16
    CARD_SIZE = (360, 330)
    CARD_GAP = 30
    CARD_IMAGE_H = 200
    CARD_COLOR = (34, 40, 58)
    CARD_HOVER_COLOR = (46, 54, 78)
    JOIN_SIZE = (380, 90)
    BACK_SIZE = (200, 70)
    GREEN = (60, 185, 75)
    GREEN_HOVER = (85, 215, 100)

    def __init__(self, app, top: int):
        self.app = app
        self.top = top
        self.category = CATEGORIES[0][0]
        self.selected: dict[str, GameMode | None] = {cid: None for cid, _ in CATEGORIES}
        self.tab_font = pygame.font.Font(None, 44)
        self.tab_font.set_bold(True)
        self.name_font = pygame.font.Font(None, 48)
        self.desc_font = pygame.font.Font(None, 28)
        self.letter_font = pygame.font.Font(None, 160)
        self.empty_font = pygame.font.Font(None, 48)
        join_font = pygame.font.Font(None, 60)
        join_font.set_bold(True)
        back_font = pygame.font.Font(None, 40)
        self.join_button = Button(pygame.Rect(0, 0, *self.JOIN_SIZE), "JOIN", join_font,
                                  self.GREEN, self.GREEN_HOVER, border_radius=10)
        self.join_button.rect.bottomright = (VIRTUAL_W - self.MARGIN_X, VIRTUAL_H - 50)
        self.back_button = Button(pygame.Rect(0, 0, *self.BACK_SIZE), "Back", back_font)
        self.back_button.rect.bottomleft = (self.MARGIN_X, VIRTUAL_H - 50)
        self.tab_rects = [pygame.Rect(self.MARGIN_X + i * (self.TAB_SIZE[0] + self.TAB_GAP),
                                      top + 30, *self.TAB_SIZE) for i in range(len(CATEGORIES))]
        self._select_default()

    def _select_default(self) -> None:
        """Przy pierwszym wejściu w zakładkę zaznacza pierwszy tryb z listy."""
        if self.selected[self.category] is None:
            modes = modes_in(self.category)
            self.selected[self.category] = modes[0] if modes else None

    def _card_rects(self) -> list[tuple[GameMode, pygame.Rect]]:
        """Układ siatki kafelków (zawija do nowego rzędu, gdy brakuje miejsca)."""
        w, h = self.CARD_SIZE
        per_row = max(1, (VIRTUAL_W - 2 * self.MARGIN_X + self.CARD_GAP) // (w + self.CARD_GAP))
        result = []
        for i, mode in enumerate(modes_in(self.category)):
            row, col = divmod(i, per_row)
            x = self.MARGIN_X + col * (w + self.CARD_GAP)
            y = self.top + 150 + row * (h + self.CARD_GAP)
            result.append((mode, pygame.Rect(x, y, w, h)))
        return result

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "close"
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        pos = self.app.mouse_virtual_pos()
        if self.back_button.hit(pos):
            return "close"
        for (category, _), rect in zip(CATEGORIES, self.tab_rects):
            if rect.collidepoint(pos):
                self.category = category
                self._select_default()
                return None
        for mode, rect in self._card_rects():
            if rect.collidepoint(pos):
                self.selected[self.category] = mode
                return None
        mode = self.selected[self.category]
        if mode is not None and self.join_button.hit(pos):
            self.app.start_game(mode)
        return None

    def draw(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        pygame.draw.rect(surface, self.BG_COLOR, (0, self.top, VIRTUAL_W, VIRTUAL_H - self.top))
        self._draw_tabs(surface, mouse)
        cards = self._card_rects()
        if not cards:
            text = self.empty_font.render("No modes yet", True, (130, 135, 150))
            surface.blit(text, text.get_rect(center=(VIRTUAL_W // 2, VIRTUAL_H // 2)))
        selected = self.selected[self.category]
        for mode, rect in cards:
            self._draw_card(surface, mode, rect, mode is selected, rect.collidepoint(mouse))
        self.join_button.enabled = selected is not None
        self.join_button.draw(surface, mouse)
        self.back_button.draw(surface, mouse)

    def _draw_tabs(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        for (category, label), rect in zip(CATEGORIES, self.tab_rects):
            active = category == self.category
            hover = rect.collidepoint(mouse)
            color = (255, 255, 255) if active else ((200, 205, 215) if hover else (120, 125, 140))
            text = self.tab_font.render(label, True, color)
            surface.blit(text, text.get_rect(center=rect.center))
            if active:
                pygame.draw.line(surface, self.ACCENT, (rect.left, rect.bottom), (rect.right, rect.bottom), 5)
        pygame.draw.line(surface, (50, 56, 76), (self.MARGIN_X, self.tab_rects[0].bottom + 2),
                         (VIRTUAL_W - self.MARGIN_X, self.tab_rects[0].bottom + 2), 2)

    def _draw_card(self, surface: pygame.Surface, mode: GameMode, rect: pygame.Rect,
                   selected: bool, hover: bool) -> None:
        pygame.draw.rect(surface, self.CARD_HOVER_COLOR if hover else self.CARD_COLOR, rect, border_radius=12)
        image_rect = pygame.Rect(rect.x + 10, rect.y + 10, rect.width - 20, self.CARD_IMAGE_H)
        draw_placeholder_image(surface, image_rect, mode.color, mode.name[:1].upper(), self.letter_font)
        name = self.name_font.render(mode.name, True, (255, 255, 255))
        surface.blit(name, (rect.x + 20, image_rect.bottom + 16))
        desc = self.desc_font.render(mode.description, True, (170, 175, 190))
        surface.blit(desc, (rect.x + 20, image_rect.bottom + 62))
        if selected:
            pygame.draw.rect(surface, self.ACCENT, rect, width=5, border_radius=12)
