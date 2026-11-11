from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from settings import (VIRTUAL_W, VIRTUAL_H, HUD_FONT_SIZE, HUD_MARGIN, HUD_COLOR, HUD_EMPTY_COLOR,
                      HP_BAR_SIZE, HP_BAR_SLANT, HP_FONT_SIZE, HP_BAR_COLOR, HP_BAR_BACK_COLOR)
from scoring import ranking
from widgets import Button

if TYPE_CHECKING:
    from entities import Player
    from weapons import Inventory


class KillFeed:
    """Log eliminacji w stylu CS:GO (prawy górny róg): zabójca, nazwa broni i wyeliminowany."""

    DURATION = 5.0  # sekundy widoczności wpisu
    MAX_ENTRIES = 5
    FONT_SIZE = 28
    MARGIN = 30
    PADDING = (14, 6)
    TEXT_COLOR = (255, 255, 255)
    WEAPON_COLOR = (255, 210, 80)
    BACK_COLOR = (0, 0, 0, 150)
    ROW_GAP = 6

    def __init__(self):
        self.font = pygame.font.Font(None, self.FONT_SIZE)
        self.entries: list[list] = []  # [zabójca, broń, ofiara, wiek]

    def add(self, killer_name: str, weapon_name: str, victim_name: str) -> None:
        self.entries.append([killer_name, weapon_name, victim_name, 0.0])
        self.entries = self.entries[-self.MAX_ENTRIES:]

    def update(self, dt: float) -> None:
        for entry in self.entries:
            entry[3] += dt
        self.entries = [e for e in self.entries if e[3] < self.DURATION]

    def draw(self, surface: pygame.Surface) -> None:
        y = self.MARGIN
        for killer, weapon, victim, _ in self.entries:
            parts = [self.font.render(killer, True, self.TEXT_COLOR),
                     self.font.render(weapon, True, self.WEAPON_COLOR),
                     self.font.render(victim, True, self.TEXT_COLOR)]
            gap = 16
            w = sum(p.get_width() for p in parts) + gap * (len(parts) - 1) + self.PADDING[0] * 2
            h = max(p.get_height() for p in parts) + self.PADDING[1] * 2
            box = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(box, self.BACK_COLOR, box.get_rect(), border_radius=6)
            x = self.PADDING[0]
            for part in parts:
                box.blit(part, (x, self.PADDING[1]))
                x += part.get_width() + gap
            surface.blit(box, (VIRTUAL_W - self.MARGIN - w, y))
            y += h + self.ROW_GAP


class NameTag:
    """Napis nad postacią - wielokrotnego użytku (gracz, boty, później inni gracze)."""

    FONT_SIZE = 32
    COLOR = (255, 255, 255)
    GAP = 8  # odstęp od górnej krawędzi postaci

    _font: pygame.font.Font | None = None

    def __init__(self, text: str):
        if NameTag._font is None:
            NameTag._font = pygame.font.Font(None, self.FONT_SIZE)
        self.image = NameTag._font.render(text, True, self.COLOR)

    def draw(self, surface: pygame.Surface, target_rect: pygame.Rect, camera_offset: pygame.Vector2) -> None:
        rect = self.image.get_rect(
            midbottom=(target_rect.centerx - round(camera_offset.x), target_rect.top - self.GAP - round(camera_offset.y))
        )
        surface.blit(self.image, rect)


class Hud:
    """Proste UI (rysowane po świecie, na stałe w rogu wirtualnego ekranu): amunicja i HP."""

    def __init__(self):
        self.font = pygame.font.Font(None, HUD_FONT_SIZE)
        self.hp_font = pygame.font.Font(None, HP_FONT_SIZE)
        self.hp_font.set_bold(True)
        self.inventory_bar = InventoryBar()

    def draw(self, surface: pygame.Surface, player: Player) -> None:
        gun = player.gun
        text = f"Ammo   {gun.ammo} / {gun.magazine_size}"
        color = HUD_COLOR if gun.ammo > 0 else HUD_EMPTY_COLOR
        image = self.font.render(text, True, color)
        surface.blit(image, image.get_rect(bottomright=(VIRTUAL_W - HUD_MARGIN, VIRTUAL_H - HUD_MARGIN)))
        self._draw_hp_bar(surface, player)
        self.inventory_bar.draw(surface, player.inventory)

    def _draw_hp_bar(self, surface: pygame.Surface, player: Player) -> None:
        """Minimalistyczny pasek HP gracza w stylu Fortnite (lewy dolny róg, zawsze zielony,
        lekko pochylony) z napisem 'hp | max'. Tylko w HUD, bez pasków nad postaciami."""
        health = player.health
        w, h = HP_BAR_SIZE
        x, y = HUD_MARGIN, VIRTUAL_H - HUD_MARGIN - h
        slant = HP_BAR_SLANT

        def parallelogram(width: float) -> list[tuple[float, float]]:
            return [(x + slant, y), (x + slant + width, y), (x + width, y + h), (x, y + h)]

        pygame.draw.polygon(surface, HP_BAR_BACK_COLOR, parallelogram(w))
        if health.hp > 0:
            pygame.draw.polygon(surface, HP_BAR_COLOR, parallelogram(w * health.fraction))
        text = self.hp_font.render(f"{math.ceil(health.hp)} | {math.ceil(health.max_hp)}", True, HUD_COLOR)
        surface.blit(text, text.get_rect(midleft=(x + slant + 12, y + h // 2)))


class InventoryBar:
    """Pasek przedmiotów w stylu Robloxa (dół ekranu, środek): kwadratowe sloty z nazwą broni
    (później zdjęcie) i biały klawisz z cyfrą pod spodem. Aktywny slot jest podświetlony."""

    SLOT_SIZE = 62
    SLOT_GAP = 8
    KEY_SIZE = (28, 24)
    BOTTOM_MARGIN = 12  # odstęp klawiszy od dolnej krawędzi ekranu
    KEY_GAP = 6  # odstęp slot -> klawisz
    SLOT_COLOR = (0, 0, 0, 150)
    SLOT_ACTIVE_COLOR = (40, 40, 40, 200)
    BORDER_COLOR = (255, 255, 255, 70)
    BORDER_ACTIVE_COLOR = (255, 210, 80)
    NAME_FONT_SIZE = 20
    NAME_COLOR = (255, 255, 255)
    KEY_COLOR = (245, 245, 245)
    KEY_SHADOW_COLOR = (150, 150, 155)
    KEY_TEXT_COLOR = (30, 30, 35)
    KEY_FONT_SIZE = 24

    def __init__(self):
        self.name_font = pygame.font.Font(None, self.NAME_FONT_SIZE)
        self.key_font = pygame.font.Font(None, self.KEY_FONT_SIZE)
        self.key_font.set_bold(True)

    def draw(self, surface: pygame.Surface, inventory: Inventory) -> None:
        count = len(inventory.guns)
        total_w = count * self.SLOT_SIZE + (count - 1) * self.SLOT_GAP
        x0 = (VIRTUAL_W - total_w) // 2
        total_h = self.SLOT_SIZE + self.KEY_GAP + self.KEY_SIZE[1]
        y = VIRTUAL_H - self.BOTTOM_MARGIN - total_h
        for i, gun in enumerate(inventory.guns):
            x = x0 + i * (self.SLOT_SIZE + self.SLOT_GAP)
            self._draw_slot(surface, x, y, gun.name, i == inventory.index)
            self._draw_key(surface, x + self.SLOT_SIZE // 2, y + self.SLOT_SIZE + self.KEY_GAP, str(i + 1))

    def _draw_slot(self, surface: pygame.Surface, x: int, y: int, name: str, active: bool) -> None:
        size = self.SLOT_SIZE
        box = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(box, self.SLOT_ACTIVE_COLOR if active else self.SLOT_COLOR, box.get_rect(), border_radius=8)
        border = self.BORDER_ACTIVE_COLOR if active else self.BORDER_COLOR
        pygame.draw.rect(box, border, box.get_rect(), width=3 if active else 2, border_radius=8)
        text = self.name_font.render(name, True, self.NAME_COLOR)
        max_w = size - 8
        if text.get_width() > max_w:  # długa nazwa: zmniejsz, żeby zmieściła się w slocie
            text = pygame.transform.smoothscale(text, (max_w, round(text.get_height() * max_w / text.get_width())))
        box.blit(text, text.get_rect(center=(size // 2, size // 2)))
        surface.blit(box, (x, y))

    def _draw_key(self, surface: pygame.Surface, center_x: int, y: int, label: str) -> None:
        """Biały klawisz klawiatury z lekkim cieniem od dołu."""
        w, h = self.KEY_SIZE
        rect = pygame.Rect(center_x - w // 2, y, w, h)
        pygame.draw.rect(surface, self.KEY_SHADOW_COLOR, rect.move(0, 2), border_radius=5)
        pygame.draw.rect(surface, self.KEY_COLOR, rect, border_radius=5)
        text = self.key_font.render(label, True, self.KEY_TEXT_COLOR)
        surface.blit(text, text.get_rect(center=rect.center))


class EliminatedScreen:
    """Ekran 'YOU HAVE BEEN ELIMINATED' z przyciskami Respawn i Quit."""

    TITLE_SIZE = 72
    BUTTON_SIZE = (320, 70)
    BUTTON_FONT_SIZE = 44
    BUTTON_COLOR = (60, 60, 75)
    BUTTON_HOVER_COLOR = (95, 95, 120)

    def __init__(self):
        self.title_font = pygame.font.Font(None, self.TITLE_SIZE)
        self.button_font = pygame.font.Font(None, self.BUTTON_FONT_SIZE)
        center_x = VIRTUAL_W // 2
        self.respawn_button = pygame.Rect(0, 0, *self.BUTTON_SIZE)
        self.respawn_button.center = (center_x, VIRTUAL_H // 2 + 30)
        self.quit_button = pygame.Rect(0, 0, *self.BUTTON_SIZE)
        self.quit_button.center = (center_x, VIRTUAL_H // 2 + 120)

    def button_at(self, pos: pygame.Vector2) -> str | None:
        """Zwraca 'respawn', 'quit' albo None - który przycisk jest pod kursorem."""
        if self.respawn_button.collidepoint(pos):
            return "respawn"
        if self.quit_button.collidepoint(pos):
            return "quit"
        return None

    def draw(self, surface: pygame.Surface, mouse_pos: pygame.Vector2) -> None:
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))
        title = self.title_font.render("YOU HAVE BEEN ELIMINATED", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(VIRTUAL_W // 2, VIRTUAL_H // 2 - 80)))
        for rect, label in ((self.respawn_button, "Respawn"), (self.quit_button, "Quit")):
            color = self.BUTTON_HOVER_COLOR if rect.collidepoint(mouse_pos) else self.BUTTON_COLOR
            pygame.draw.rect(surface, color, rect, border_radius=8)
            text = self.button_font.render(label, True, (255, 255, 255))
            surface.blit(text, text.get_rect(center=rect.center))


class EscMenu:
    """Menu pod ESC w trakcie gry (na razie tylko Leave - powrót do menu głównego)."""

    PANEL_SIZE = (560, 320)
    PANEL_COLOR = (18, 22, 34)
    BORDER_COLOR = (255, 210, 80)
    BUTTON_SIZE = (360, 80)
    LEAVE_COLOR = (170, 55, 55)
    LEAVE_HOVER_COLOR = (205, 75, 75)

    def __init__(self):
        self.title_font = pygame.font.Font(None, 72)
        self.title_font.set_bold(True)
        self.hint_font = pygame.font.Font(None, 28)
        button_font = pygame.font.Font(None, 50)
        self.panel = pygame.Rect(0, 0, *self.PANEL_SIZE)
        self.panel.center = (VIRTUAL_W // 2, VIRTUAL_H // 2)
        self.leave_button = Button(pygame.Rect(0, 0, *self.BUTTON_SIZE), "Leave", button_font,
                                   self.LEAVE_COLOR, self.LEAVE_HOVER_COLOR, border_radius=10)
        self.leave_button.rect.center = (self.panel.centerx, self.panel.centery + 20)

    def button_at(self, pos: pygame.Vector2) -> str | None:
        return "leave" if self.leave_button.hit(pos) else None

    def draw(self, surface: pygame.Surface, mouse_pos: pygame.Vector2) -> None:
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))
        pygame.draw.rect(surface, self.PANEL_COLOR, self.panel, border_radius=14)
        pygame.draw.rect(surface, self.BORDER_COLOR, self.panel, width=3, border_radius=14)
        title = self.title_font.render("MENU", True, (255, 255, 255))
        surface.blit(title, title.get_rect(midtop=(self.panel.centerx, self.panel.top + 30)))
        self.leave_button.draw(surface, mouse_pos)
        hint = self.hint_font.render("Press ESC to resume", True, (150, 155, 170))
        surface.blit(hint, hint.get_rect(midbottom=(self.panel.centerx, self.panel.bottom - 25)))


class MatchHud:
    """Góra ekranu w trybie z punktacją: czas do końca meczu, pod nim placeholdery zdjęć graczy
    (od najwyższego wyniku), a pod nimi punkty. Gracz ma żółtą ramkę."""

    TIMER_FONT_SIZE = 64
    POINTS_FONT_SIZE = 26
    PORTRAIT = 54
    GAP = 10
    TOP = 18
    ACCENT = (255, 210, 80)

    def __init__(self):
        self.timer_font = pygame.font.Font(None, self.TIMER_FONT_SIZE)
        self.timer_font.set_bold(True)
        self.points_font = pygame.font.Font(None, self.POINTS_FONT_SIZE)
        self.points_font.set_bold(True)

    def draw(self, surface: pygame.Surface, time_left: float, participants: list) -> None:
        seconds = max(0, math.ceil(time_left))
        timer = self.timer_font.render(f"{seconds // 60}:{seconds % 60:02d}", True, (255, 255, 255))
        timer_rect = timer.get_rect(midtop=(VIRTUAL_W // 2, self.TOP))
        surface.blit(timer, timer_rect)
        ranked = ranking(participants)
        count = len(ranked)
        total_w = count * self.PORTRAIT + (count - 1) * self.GAP
        x0 = (VIRTUAL_W - total_w) // 2
        y = timer_rect.bottom + 10
        for i, p in enumerate(ranked):
            rect = pygame.Rect(x0 + i * (self.PORTRAIT + self.GAP), y, self.PORTRAIT, self.PORTRAIT)
            pygame.draw.rect(surface, p.color, rect, border_radius=6)
            border = self.ACCENT if p.is_player else (0, 0, 0)
            pygame.draw.rect(surface, border, rect, width=3, border_radius=6)
            points = self.points_font.render(str(p.points), True, self.ACCENT if p.is_player else (255, 255, 255))
            surface.blit(points, points.get_rect(midtop=(rect.centerx, rect.bottom + 4)))
