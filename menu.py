from __future__ import annotations

import math

import pygame

from menu_tabs import InventoryView, SettingsView, ShopView
from play_menu import PlayCard
from scene import Scene
from settings import VIRTUAL_W, VIRTUAL_H, GRID_STEP, GRID_COLOR
from widgets import Button


class MenuScene(Scene):
    """Menu główne: górny pasek z zakładkami (PLAY / INVENTORY / SHOP / SETTINGS),
    saldo Tokens, miniaturka PFP oraz treść wybranej zakładki."""

    BAR_H = 90
    BG_COLOR = (22, 28, 44)
    BAR_COLOR = (12, 15, 24)
    ACCENT = (255, 210, 80)
    GREEN = (60, 185, 75)
    GREEN_HOVER = (85, 215, 100)
    TITLE_SIZE = 44
    PLAY_SIZE = (440, 110)
    PLAY_FONT_SIZE = 72
    QUIT_SIZE = (130, 52)
    CHAR_SIZE = 170  # placeholder postaci w lobby (kolor z założonego skina)
    CHAR_NAME_SIZE = 60
    TABS = ("PLAY", "INVENTORY", "SHOP", "SETTINGS")

    def __init__(self, app):
        super().__init__(app)
        self.time = 0.0
        self.active_tab = "PLAY"
        self.title_font = pygame.font.Font(None, self.TITLE_SIZE)
        self.title_font.set_bold(True)
        self.tab_font = pygame.font.Font(None, 36)
        self.tab_font.set_bold(True)
        self.bar_font = pygame.font.Font(None, 32)
        self.bar_font.set_bold(True)
        self.name_font = pygame.font.Font(None, self.CHAR_NAME_SIZE)
        small_font = pygame.font.Font(None, 34)
        play_font = pygame.font.Font(None, self.PLAY_FONT_SIZE)
        play_font.set_bold(True)
        self.play_button = Button(pygame.Rect(0, 0, *self.PLAY_SIZE), "PLAY", play_font,
                                  self.GREEN, self.GREEN_HOVER, border_radius=12)
        self.play_button.rect.center = (VIRTUAL_W // 2, VIRTUAL_H - 130)
        self.quit_button = Button(pygame.Rect(0, 0, *self.QUIT_SIZE), "Quit", small_font)
        self.quit_button.rect.midright = (VIRTUAL_W - 28, self.BAR_H // 2)

        self.tab_rects = [
            pygame.Rect(450 + i * 175, 18, 162, 54) for i in range(len(self.TABS))
        ]

        self.card = PlayCard(self.app, top=self.BAR_H)
        self.card_open = False
        self.views = {
            "INVENTORY": InventoryView(self.app, top=self.BAR_H),
            "SHOP": ShopView(self.app, top=self.BAR_H),
            "SETTINGS": SettingsView(self.app, top=self.BAR_H),
        }

    def handle_event(self, event: pygame.event.Event) -> None:
        pos = self.app.mouse_virtual_pos()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.quit_button.hit(pos):
                self.app.quit()
                return
            # Zakładki na górnym pasku (zablokowane tylko w trakcie kręcenia ruletki)
            inv_view = self.views["INVENTORY"]
            roulette_busy = self.active_tab == "INVENTORY" and inv_view.roulette is not None and not inv_view.roulette.done
            if not roulette_busy:
                for tab, rect in zip(self.TABS, self.tab_rects):
                    if rect.collidepoint(pos):
                        self.active_tab = tab
                        if tab != "PLAY":
                            self.card_open = False
                        return

        if self.active_tab == "PLAY":
            if self.card_open:
                if self.card.handle_event(event) == "close":
                    self.card_open = False
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.play_button.hit(pos):
                self.card_open = True
        else:
            self.views[self.active_tab].handle_event(event, pos)

    def update(self, dt: float) -> None:
        self.time += dt
        if self.active_tab != "PLAY":
            self.views[self.active_tab].update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        mouse = self.app.mouse_virtual_pos()
        self._draw_background(surface, show_character=(self.active_tab == "PLAY" and not self.card_open))
        if self.active_tab == "PLAY":
            if self.card_open:
                self.card.draw(surface, mouse)
            else:
                self.play_button.draw(surface, mouse)
        else:
            self.views[self.active_tab].draw(surface, mouse)
        self._draw_bar(surface, mouse)

    def _draw_background(self, surface: pygame.Surface, show_character: bool) -> None:
        surface.fill(self.BG_COLOR)
        for x in range(0, VIRTUAL_W, GRID_STEP):
            pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, VIRTUAL_H))
        for y in range(0, VIRTUAL_H, GRID_STEP):
            pygame.draw.line(surface, GRID_COLOR, (0, y), (VIRTUAL_W, y))
        if not show_character:
            return
        # Postać w lobby (placeholder) lekko "lewituje", pod nią cień
        cx, cy = VIRTUAL_W // 2, VIRTUAL_H // 2 + 20
        bob = math.sin(self.time * 2.0) * 10
        shadow = pygame.Surface((self.CHAR_SIZE, 36), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
        surface.blit(shadow, shadow.get_rect(center=(cx, cy + self.CHAR_SIZE // 2 + 50)))
        body = pygame.Rect(0, 0, self.CHAR_SIZE, self.CHAR_SIZE)
        body.center = (cx, cy + bob)
        pygame.draw.rect(surface, self.app.account.player_color(), body)
        name = self.name_font.render(self.app.account.name, True, (255, 255, 255))
        surface.blit(name, name.get_rect(midbottom=(cx, body.top - 24)))

    def _draw_bar(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        pygame.draw.rect(surface, self.BAR_COLOR, (0, 0, VIRTUAL_W, self.BAR_H))
        pygame.draw.line(surface, self.ACCENT, (0, self.BAR_H), (VIRTUAL_W, self.BAR_H), 3)
        title = self.title_font.render("CHRISTMAS ROYALE", True, (255, 255, 255))
        surface.blit(title, title.get_rect(midleft=(32, self.BAR_H // 2)))

        for tab, rect in zip(self.TABS, self.tab_rects):
            active = tab == self.active_tab
            hover = rect.collidepoint(mouse)
            if active:
                pygame.draw.rect(surface, (34, 42, 66), rect, border_radius=8)
                pygame.draw.line(surface, self.ACCENT, (rect.left + 12, rect.bottom - 3),
                                 (rect.right - 12, rect.bottom - 3), 3)
                col = (255, 255, 255)
            else:
                col = (210, 215, 230) if hover else (130, 138, 160)
            t_surf = self.tab_font.render(tab, True, col)
            surface.blit(t_surf, t_surf.get_rect(center=rect.center))

        # Prawa strona paska: Tokens, PFP, nazwa gracza i Quit
        acc = self.app.account
        tokens = self.bar_font.render(f"{acc.tokens} Tokens", True, self.ACCENT)
        name = self.bar_font.render(acc.name, True, (255, 255, 255))
        pfp_rect = pygame.Rect(0, 0, 46, 46)
        pfp_rect.midright = (self.quit_button.rect.left - 24, self.BAR_H // 2)
        pfp_img = acc.load_pfp_surface((46, 46))
        if pfp_img is not None:
            surface.blit(pfp_img, pfp_rect)
        else:
            pygame.draw.rect(surface, acc.player_color(), pfp_rect, border_radius=6)
        pygame.draw.rect(surface, self.ACCENT, pfp_rect, width=2, border_radius=6)
        name_rect = name.get_rect(midright=(pfp_rect.left - 14, self.BAR_H // 2))
        surface.blit(name, name_rect)
        surface.blit(tokens, tokens.get_rect(midright=(name_rect.left - 32, self.BAR_H // 2)))
        self.quit_button.draw(surface, mouse)
