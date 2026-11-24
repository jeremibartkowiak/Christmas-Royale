from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from settings import (VIRTUAL_W, VIRTUAL_H, HUD_FONT_SIZE, HUD_MARGIN, HUD_COLOR, HUD_EMPTY_COLOR,
                      HP_BAR_SIZE, HP_BAR_SLANT, HP_FONT_SIZE, HP_BAR_COLOR, HP_BAR_BACK_COLOR,
                      CROSSHAIR_COLOR)
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
        if gun is None:
            text, color = "No weapon", HUD_EMPTY_COLOR
        else:
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
        if count == 0:
            return
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


class Crosshair:
    """Dynamiczny celownik (4 kreski + kropka na środku), który rozszerza się zależnie od spreadu."""

    BASE_GAP = 6.0  # minimalny odstęp kresek od środka przy spread = 0° (px)
    PX_PER_DEG = 6.0  # ile pikseli na 1° rozrzutu
    LINE_LEN = 12
    LINE_THICKNESS = 3
    DOT_RADIUS = 2
    SMOOTH_SPEED = 18.0  # szybkość płynnego rozsuwania/zwężania kresek

    def __init__(self, color: tuple[int, int, int] = CROSSHAIR_COLOR):
        self.color = color
        self.display_spread = 0.0

    def update(self, dt: float, target_spread: float) -> None:
        t = 1 - math.exp(-self.SMOOTH_SPEED * dt)
        self.display_spread += (target_spread - self.display_spread) * t

    def draw(self, surface: pygame.Surface, pos: pygame.Vector2) -> None:
        cx, cy = round(pos.x), round(pos.y)
        gap = round(self.BASE_GAP + self.display_spread * self.PX_PER_DEG)
        pygame.draw.circle(surface, self.color, (cx, cy), self.DOT_RADIUS)
        # 4 kreski: góra, dół, lewo, prawo
        pygame.draw.line(surface, self.color, (cx, cy - gap), (cx, cy - gap - self.LINE_LEN), self.LINE_THICKNESS)
        pygame.draw.line(surface, self.color, (cx, cy + gap), (cx, cy + gap + self.LINE_LEN), self.LINE_THICKNESS)
        pygame.draw.line(surface, self.color, (cx - gap, cy), (cx - gap - self.LINE_LEN, cy), self.LINE_THICKNESS)
        pygame.draw.line(surface, self.color, (cx + gap, cy), (cx + gap + self.LINE_LEN, cy), self.LINE_THICKNESS)


class ProximityPrompt:
    """Podpowiedź interakcji w świecie gry (w stylu Robloxa): [klawisz] akcja + pasek przytrzymania."""

    BACK_COLOR = (15, 18, 28, 210)
    BORDER_COLOR = (255, 210, 80)
    KEY_COLOR = (245, 245, 245)
    KEY_TEXT_COLOR = (25, 25, 32)
    TEXT_COLOR = (255, 255, 255)
    BAR_COLOR = (255, 210, 80)
    BAR_BACK_COLOR = (55, 60, 78)
    GAP = 14

    def __init__(self, key_label: str = "E", action_text: str = "Open"):
        self.key_label = key_label
        self.action_text = action_text
        self.key_font = pygame.font.Font(None, 28)
        self.key_font.set_bold(True)
        self.text_font = pygame.font.Font(None, 28)

    def draw(self, surface: pygame.Surface, target_rect: pygame.Rect, camera_offset: pygame.Vector2,
             progress: float = 0.0) -> None:
        key_surf = self.key_font.render(self.key_label, True, self.KEY_TEXT_COLOR)
        text_surf = self.text_font.render(self.action_text, True, self.TEXT_COLOR)
        key_size = max(28, key_surf.get_width() + 12)
        pad_x, pad_y, gap = 10, 8, 8
        bar_h = 5 if progress > 0 else 0
        w = pad_x * 2 + key_size + gap + text_surf.get_width()
        h = pad_y * 2 + max(key_size, text_surf.get_height()) + (bar_h + 6 if bar_h else 0)
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(box, self.BACK_COLOR, box.get_rect(), border_radius=8)
        pygame.draw.rect(box, self.BORDER_COLOR, box.get_rect(), width=2, border_radius=8)
        key_rect = pygame.Rect(pad_x, pad_y, key_size, key_size)
        pygame.draw.rect(box, self.KEY_COLOR, key_rect, border_radius=5)
        box.blit(key_surf, key_surf.get_rect(center=key_rect.center))
        box.blit(text_surf, text_surf.get_rect(midleft=(key_rect.right + gap, key_rect.centery)))
        if bar_h:
            bar_rect = pygame.Rect(pad_x, h - pad_y - bar_h + 2, w - pad_x * 2, bar_h)
            pygame.draw.rect(box, self.BAR_BACK_COLOR, bar_rect, border_radius=3)
            fill = bar_rect.copy()
            fill.width = max(1, round(bar_rect.width * min(1.0, progress)))
            pygame.draw.rect(box, self.BAR_COLOR, fill, border_radius=3)
        pos_rect = box.get_rect(
            midbottom=(target_rect.centerx - round(camera_offset.x), target_rect.top - self.GAP - round(camera_offset.y))
        )
        surface.blit(box, pos_rect)


class BattleRoyaleHud:
    """HUD dla Battle Royale: minimapa z fioletową strefą (lewy górny róg),
    timer fazy strefy oraz licznik żywych i eliminacji (góra ekranu)."""

    MAP_SIZE = 220
    MAP_POS = (30, 30)
    MAP_BG = (22, 28, 42)
    MAP_OBSTACLE = (90, 96, 114)
    MAP_BORDER = (255, 210, 80)

    def __init__(self, bounds: pygame.Rect, obstacles: list):
        self.bounds = bounds
        self.scale_x = self.MAP_SIZE / bounds.width
        self.scale_y = self.MAP_SIZE / bounds.height
        self.timer_font = pygame.font.Font(None, 52)
        self.timer_font.set_bold(True)
        self.stat_font = pygame.font.Font(None, 32)
        self.stat_font.set_bold(True)
        # Statyczne tło minimapy (przeszkody rysowane raz dla wydajności)
        self.map_bg = pygame.Surface((self.MAP_SIZE, self.MAP_SIZE))
        self.map_bg.fill(self.MAP_BG)
        for obj in obstacles:
            r = obj.rect
            mr = pygame.Rect(
                round((r.left - bounds.left) * self.scale_x),
                round((r.top - bounds.top) * self.scale_y),
                max(2, round(r.width * self.scale_x)),
                max(2, round(r.height * self.scale_y)),
            )
            pygame.draw.rect(self.map_bg, self.MAP_OBSTACLE, mr)
        self._storm_surf = pygame.Surface((self.MAP_SIZE, self.MAP_SIZE))
        self._storm_surf.set_colorkey((0, 0, 0))
        self._storm_surf.set_alpha(120)

    def _to_map(self, pos: pygame.Vector2) -> tuple[int, int]:
        return (
            round((pos.x - self.bounds.left) * self.scale_x),
            round((pos.y - self.bounds.top) * self.scale_y),
        )

    def draw(self, surface: pygame.Surface, player_pos: pygame.Vector2, zone,
             alive_count: int, eliminations: int) -> None:
        self._draw_minimap(surface, player_pos, zone)
        self._draw_top_stats(surface, zone, alive_count, eliminations)

    def _draw_minimap(self, surface: pygame.Surface, player_pos: pygame.Vector2, zone) -> None:
        mx, my = self.MAP_POS
        map_img = self.map_bg.copy()
        # Fioletowa strefa na minimapie
        zc = self._to_map(zone.center)
        zr = max(0, round(zone.radius * self.scale_x))
        self._storm_surf.fill((135, 45, 205))
        if zr > 0:
            pygame.draw.circle(self._storm_surf, (0, 0, 0), zc, zr)
        map_img.blit(self._storm_surf, (0, 0))
        if zr > 0:
            pygame.draw.circle(map_img, (195, 95, 255), zc, zr, width=2)
        # Kolejna bezpieczna strefa (biały okrąg)
        nc = self._to_map(zone.target_center)
        nr = max(0, round(zone.target_radius * self.scale_x))
        if nr > 0 and zone.state != "done":
            pygame.draw.circle(map_img, (230, 235, 255), nc, nr, width=1)
        # Pozycja gracza
        pc = self._to_map(player_pos)
        pygame.draw.circle(map_img, (40, 140, 255), pc, 5)
        pygame.draw.circle(map_img, (255, 255, 255), pc, 5, width=1)
        surface.blit(map_img, (mx, my))
        pygame.draw.rect(surface, self.MAP_BORDER, (mx, my, self.MAP_SIZE, self.MAP_SIZE), width=2)

    def _draw_top_stats(self, surface: pygame.Surface, zone, alive_count: int, eliminations: int) -> None:
        secs = max(0, math.ceil(zone.time_left))
        if zone.state == "done":
            label, col = "FINAL ZONE", (220, 120, 255)
        elif zone.state == "shrink":
            label, col = f"STORM CLOSING  {secs // 60}:{secs % 60:02d}", (220, 120, 255)
        else:
            label, col = f"STORM IN  {secs // 60}:{secs % 60:02d}", (255, 255, 255)
        timer = self.timer_font.render(label, True, col)
        timer_rect = timer.get_rect(midtop=(VIRTUAL_W // 2, 18))
        surface.blit(timer, timer_rect)

        stats = self.stat_font.render(f"Alive: {alive_count}     Eliminations: {eliminations}", True, (255, 210, 80))
        box = pygame.Surface((stats.get_width() + 28, stats.get_height() + 14), pygame.SRCALPHA)
        pygame.draw.rect(box, (0, 0, 0, 150), box.get_rect(), border_radius=8)
        box.blit(stats, (14, 7))
        surface.blit(box, box.get_rect(midtop=(VIRTUAL_W // 2, timer_rect.bottom + 8)))


class BattleRoyaleEndScreen:
    """Ekran końcowy Battle Royale (Victory Royale lub Eliminated + miejsce i eliminacje)."""

    def __init__(self):
        self.title_font = pygame.font.Font(None, 86)
        self.title_font.set_bold(True)
        self.info_font = pygame.font.Font(None, 48)
        btn_font = pygame.font.Font(None, 44)
        cx = VIRTUAL_W // 2
        self.again_button = Button(pygame.Rect(0, 0, 320, 72), "Play Again", btn_font,
                                   (60, 175, 75), (85, 205, 100), border_radius=10)
        self.again_button.rect.center = (cx - 180, VIRTUAL_H // 2 + 110)
        self.menu_button = Button(pygame.Rect(0, 0, 320, 72), "Main Menu", btn_font,
                                  (60, 65, 82), (90, 96, 120), border_radius=10)
        self.menu_button.rect.center = (cx + 180, VIRTUAL_H // 2 + 110)

    def button_at(self, pos: pygame.Vector2) -> str | None:
        if self.again_button.hit(pos):
            return "again"
        if self.menu_button.hit(pos):
            return "menu"
        return None

    def draw(self, surface: pygame.Surface, mouse_pos: pygame.Vector2, victory: bool,
             place: int, total: int, eliminations: int) -> None:
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surface.blit(overlay, (0, 0))
        title_text = "VICTORY ROYALE!" if victory else "YOU WERE ELIMINATED"
        title_color = (255, 210, 60) if victory else (255, 95, 95)
        title = self.title_font.render(title_text, True, title_color)
        surface.blit(title, title.get_rect(center=(VIRTUAL_W // 2, VIRTUAL_H // 2 - 100)))
        info = self.info_font.render(f"Place: #{place} / {total}     Eliminations: {eliminations}",
                                     True, (255, 255, 255))
        surface.blit(info, info.get_rect(center=(VIRTUAL_W // 2, VIRTUAL_H // 2 - 15)))
        self.again_button.draw(surface, mouse_pos)
        self.menu_button.draw(surface, mouse_pos)
