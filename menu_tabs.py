"""Widoki zakładek menu głównego: INVENTORY (z ruletką CS:GO), SHOP (Tokens) i SETTINGS (nazwa + PFP)."""
from __future__ import annotations

import os
import random
import tkinter
import tkinter.filedialog

import pygame

from account import Account, PFP_DIR
from items import ITEMS, SHOP_ITEMS, ItemDef, roll_case_item
from settings import VIRTUAL_W, VIRTUAL_H
from widgets import Button


def _draw_item_preview(surface: pygame.Surface, rect: pygame.Rect, item: ItemDef) -> None:
    """Placeholder grafiki przedmiotu (skrzynka / skin gracza / skin broni) - do podmiany na .png."""
    if item.kind == "player_skin":
        box = pygame.Rect(0, 0, 74, 74)
        box.center = rect.center
        pygame.draw.rect(surface, item.color, box, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), box, width=2, border_radius=8)
    elif item.kind == "weapon_skin":
        bar = pygame.Rect(0, 0, 110, 26)
        bar.center = rect.center
        pygame.draw.rect(surface, item.color, bar, border_radius=4)
        pygame.draw.rect(surface, (255, 255, 255), bar, width=2, border_radius=4)
    else:  # case
        crate = pygame.Rect(0, 0, 84, 66)
        crate.center = rect.center
        pygame.draw.rect(surface, item.color, crate, border_radius=8)
        pygame.draw.line(surface, (255, 210, 80), (crate.left, crate.centery - 8), (crate.right, crate.centery - 8), 4)
        pygame.draw.rect(surface, (255, 210, 80), crate, width=3, border_radius=8)


class CaseRoulette:
    """Animowana ruletka otwierania skrzynki w stylu CS:GO."""

    STRIP_LEN = 46
    WIN_INDEX = 37
    TILE_W = 160
    TILE_H = 160
    TILE_GAP = 14
    DURATION = 3.8  # sekundy kręcenia

    def __init__(self, case_def: ItemDef, winner: ItemDef):
        self.case_def = case_def
        self.winner = winner
        self.time = 0.0
        self.done = False
        self.strip: list[ItemDef] = []
        for i in range(self.STRIP_LEN):
            self.strip.append(winner if i == self.WIN_INDEX else roll_case_item(case_def.id))
        step = self.TILE_W + self.TILE_GAP
        jitter = random.uniform(-self.TILE_W * 0.32, self.TILE_W * 0.32)
        self.target_offset = self.WIN_INDEX * step + self.TILE_W / 2 + jitter
        self.title_font = pygame.font.Font(None, 56)
        self.title_font.set_bold(True)
        self.name_font = pygame.font.Font(None, 28)
        self.win_font = pygame.font.Font(None, 46)
        self.win_font.set_bold(True)
        btn_font = pygame.font.Font(None, 44)
        self.collect_button = Button(pygame.Rect(0, 0, 260, 68), "Collect", btn_font,
                                     (60, 185, 75), (85, 215, 100), border_radius=10)
        self.collect_button.rect.center = (VIRTUAL_W // 2, VIRTUAL_H // 2 + 210)

    def update(self, dt: float) -> None:
        if not self.done:
            self.time = min(self.DURATION, self.time + dt)
            if self.time >= self.DURATION:
                self.done = True

    def handle_event(self, event: pygame.event.Event, mouse: pygame.Vector2) -> str | None:
        if self.done and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.collect_button.hit(mouse):
                return "close"
        if self.done and event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
            return "close"
        return None

    def draw(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        shade = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 200))
        surface.blit(shade, (0, 0))

        title = self.title_font.render(f"OPENING {self.case_def.name.upper()}", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(VIRTUAL_W // 2, VIRTUAL_H // 2 - 200)))

        # Okno paska ruletki
        win_rect = pygame.Rect(0, 0, 1040, 220)
        win_rect.center = (VIRTUAL_W // 2, VIRTUAL_H // 2 - 20)
        pygame.draw.rect(surface, (18, 22, 34), win_rect, border_radius=14)
        pygame.draw.rect(surface, (70, 80, 110), win_rect, width=3, border_radius=14)

        p = self.time / self.DURATION
        eased = 1.0 - (1.0 - p) ** 4  # płynne wyhamowanie
        scroll_x = self.target_offset * eased
        step = self.TILE_W + self.TILE_GAP

        old_clip = surface.get_clip()
        surface.set_clip(win_rect.inflate(-12, -12))
        for i, item in enumerate(self.strip):
            tx = round(win_rect.centerx - scroll_x + i * step)
            if tx + self.TILE_W < win_rect.left or tx > win_rect.right:
                continue
            tile = pygame.Rect(tx, win_rect.centery - self.TILE_H // 2, self.TILE_W, self.TILE_H)
            pygame.draw.rect(surface, (32, 38, 56), tile, border_radius=10)
            pygame.draw.rect(surface, item.rarity_color, tile, width=4, border_radius=10)
            _draw_item_preview(surface, pygame.Rect(tile.x, tile.y + 8, tile.width, 108), item)
            lbl = self.name_font.render(item.name, True, (240, 240, 245))
            if lbl.get_width() > tile.width - 12:
                lbl = pygame.transform.smoothscale(lbl, (tile.width - 12, round(lbl.get_height() * (tile.width - 12) / lbl.get_width())))
            surface.blit(lbl, lbl.get_rect(midbottom=(tile.centerx, tile.bottom - 10)))
        surface.set_clip(old_clip)

        # Złoty znacznik pośrodku
        pygame.draw.line(surface, (255, 210, 80), (win_rect.centerx, win_rect.top - 8),
                         (win_rect.centerx, win_rect.bottom + 8), 4)

        if self.done:
            won = self.win_font.render(f"{self.winner.name}  ({self.winner.rarity_label})",
                                       True, self.winner.rarity_color)
            surface.blit(won, won.get_rect(center=(VIRTUAL_W // 2, win_rect.bottom + 46)))
            self.collect_button.draw(surface, mouse)


class InventoryView:
    """Zakładka INVENTORY: posiadane skiny i skrzynki + otwieranie skrzynek."""

    CARD_SIZE = (250, 260)
    GAP = 24
    MARGIN_X = 90

    def __init__(self, app, top: int):
        self.app = app
        self.top = top
        self.roulette: CaseRoulette | None = None
        self.title_font = pygame.font.Font(None, 46)
        self.title_font.set_bold(True)
        self.name_font = pygame.font.Font(None, 30)
        self.rarity_font = pygame.font.Font(None, 24)
        self.btn_font = pygame.font.Font(None, 30)
        self.empty_font = pygame.font.Font(None, 44)

    def _card_rects(self) -> list[tuple[int, ItemDef, pygame.Rect]]:
        w, h = self.CARD_SIZE
        per_row = max(1, (VIRTUAL_W - 2 * self.MARGIN_X + self.GAP) // (w + self.GAP))
        out = []
        for i, iid in enumerate(self.app.account.items):
            item = ITEMS.get(iid)
            if item is None:
                continue
            row, col = divmod(i, per_row)
            x = self.MARGIN_X + col * (w + self.GAP)
            y = self.top + 95 + row * (h + self.GAP)
            out.append((i, item, pygame.Rect(x, y, w, h)))
        return out

    def update(self, dt: float) -> None:
        if self.roulette is not None:
            self.roulette.update(dt)

    def handle_event(self, event: pygame.event.Event, mouse: pygame.Vector2) -> None:
        if self.roulette is not None:
            if self.roulette.handle_event(event, mouse) == "close":
                self.roulette = None
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        for _, item, rect in self._card_rects():
            btn_rect = pygame.Rect(rect.x + 18, rect.bottom - 52, rect.width - 36, 38)
            if btn_rect.collidepoint(mouse) or rect.collidepoint(mouse):
                if item.kind == "case":
                    winner = roll_case_item(item.id)
                    if self.app.account.open_case(item.id, winner.id):
                        self.roulette = CaseRoulette(item, winner)
                else:
                    self.app.account.toggle_equip(item.id)
                return

    def draw(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        title = self.title_font.render(f"INVENTORY ({len(self.app.account.items)} items)", True, (255, 255, 255))
        surface.blit(title, (self.MARGIN_X, self.top + 30))
        cards = self._card_rects()
        if not cards:
            empty = self.empty_font.render("Your inventory is empty. Visit the SHOP!", True, (150, 155, 175))
            surface.blit(empty, empty.get_rect(center=(VIRTUAL_W // 2, VIRTUAL_H // 2)))
        for _, item, rect in cards:
            equipped = self.app.account.is_equipped(item.id)
            bg = (42, 50, 74) if rect.collidepoint(mouse) else (28, 34, 52)
            pygame.draw.rect(surface, bg, rect, border_radius=12)
            pygame.draw.rect(surface, item.rarity_color, rect, width=3, border_radius=12)
            _draw_item_preview(surface, pygame.Rect(rect.x, rect.y + 18, rect.width, 118), item)
            name = self.name_font.render(item.name, True, (255, 255, 255))
            surface.blit(name, name.get_rect(midtop=(rect.centerx, rect.y + 140)))
            rar = self.rarity_font.render(item.rarity_label, True, item.rarity_color)
            surface.blit(rar, rar.get_rect(midtop=(rect.centerx, rect.y + 170)))

            btn_rect = pygame.Rect(rect.x + 18, rect.bottom - 52, rect.width - 36, 38)
            if item.kind == "case":
                btn_col, btn_lbl = (195, 145, 45), "Open Case"
            elif equipped:
                btn_col, btn_lbl = (60, 175, 75), "EQUIPPED"
            else:
                btn_col, btn_lbl = (65, 72, 95), "Equip"
            pygame.draw.rect(surface, btn_col, btn_rect, border_radius=8)
            bt = self.btn_font.render(btn_lbl, True, (255, 255, 255))
            surface.blit(bt, bt.get_rect(center=btn_rect.center))

        if self.roulette is not None:
            self.roulette.draw(surface, mouse)


class ShopView:
    """Zakładka SHOP: kupowanie skrzynek i skinów za walutę Tokens."""

    CARD_SIZE = (260, 280)
    GAP = 24
    MARGIN_X = 90

    def __init__(self, app, top: int):
        self.app = app
        self.top = top
        self.message = ""
        self.message_timer = 0.0
        self.title_font = pygame.font.Font(None, 46)
        self.title_font.set_bold(True)
        self.name_font = pygame.font.Font(None, 30)
        self.rarity_font = pygame.font.Font(None, 24)
        self.btn_font = pygame.font.Font(None, 30)
        self.msg_font = pygame.font.Font(None, 34)

    def _card_rects(self) -> list[tuple[ItemDef, pygame.Rect]]:
        w, h = self.CARD_SIZE
        per_row = max(1, (VIRTUAL_W - 2 * self.MARGIN_X + self.GAP) // (w + self.GAP))
        out = []
        for i, item in enumerate(SHOP_ITEMS):
            row, col = divmod(i, per_row)
            x = self.MARGIN_X + col * (w + self.GAP)
            y = self.top + 95 + row * (h + self.GAP)
            out.append((item, pygame.Rect(x, y, w, h)))
        return out

    def update(self, dt: float) -> None:
        if self.message_timer > 0:
            self.message_timer = max(0.0, self.message_timer - dt)
            if self.message_timer == 0:
                self.message = ""

    def handle_event(self, event: pygame.event.Event, mouse: pygame.Vector2) -> None:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        for item, rect in self._card_rects():
            btn_rect = pygame.Rect(rect.x + 18, rect.bottom - 54, rect.width - 36, 40)
            if btn_rect.collidepoint(mouse):
                if self.app.account.buy_item(item.id):
                    self.message = f"Bought {item.name}!"
                else:
                    self.message = "Not enough Tokens!"
                self.message_timer = 2.5
                return

    def draw(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        title = self.title_font.render("ITEM SHOP", True, (255, 255, 255))
        surface.blit(title, (self.MARGIN_X, self.top + 30))
        if self.message:
            msg = self.msg_font.render(self.message, True, (255, 210, 80))
            surface.blit(msg, msg.get_rect(midright=(VIRTUAL_W - self.MARGIN_X, self.top + 48)))

        tokens = self.app.account.tokens
        for item, rect in self._card_rects():
            pygame.draw.rect(surface, (28, 34, 52), rect, border_radius=12)
            pygame.draw.rect(surface, item.rarity_color, rect, width=3, border_radius=12)
            _draw_item_preview(surface, pygame.Rect(rect.x, rect.y + 18, rect.width, 120), item)
            name = self.name_font.render(item.name, True, (255, 255, 255))
            surface.blit(name, name.get_rect(midtop=(rect.centerx, rect.y + 144)))
            rar = self.rarity_font.render(f"{item.rarity_label}  •  {item.kind.replace('_', ' ').title()}",
                                          True, item.rarity_color)
            surface.blit(rar, rar.get_rect(midtop=(rect.centerx, rect.y + 174)))

            can_buy = tokens >= (item.price or 0)
            btn_rect = pygame.Rect(rect.x + 18, rect.bottom - 54, rect.width - 36, 40)
            hover = btn_rect.collidepoint(mouse) and can_buy
            col = (85, 215, 100) if hover else ((60, 175, 75) if can_buy else (55, 58, 70))
            pygame.draw.rect(surface, col, btn_rect, border_radius=8)
            bt = self.btn_font.render(f"Buy  {item.price} Tokens", True, (255, 255, 255) if can_buy else (140, 145, 160))
            surface.blit(bt, bt.get_rect(center=btn_rect.center))


class SettingsView:
    """Zakładka SETTINGS: zmiana nazwy gracza oraz upload/wybór własnego PFP (.png)."""

    MARGIN_X = 120

    def __init__(self, app, top: int):
        self.app = app
        self.top = top
        self.name_input = app.account.name
        self.editing_name = False
        self.status = ""
        self.title_font = pygame.font.Font(None, 48)
        self.title_font.set_bold(True)
        self.label_font = pygame.font.Font(None, 36)
        self.input_font = pygame.font.Font(None, 40)
        self.small_font = pygame.font.Font(None, 28)

        self.input_rect = pygame.Rect(self.MARGIN_X, top + 145, 420, 56)
        self.save_button = Button(pygame.Rect(self.input_rect.right + 18, top + 145, 150, 56),
                                  "Save", self.label_font, (60, 175, 75), (85, 205, 100))
        self.upload_button = Button(pygame.Rect(self.MARGIN_X + 160, top + 310, 250, 56),
                                    "Upload PNG...", self.label_font, (70, 130, 210), (95, 155, 235))
        self.clear_button = Button(pygame.Rect(self.MARGIN_X + 430, top + 310, 160, 56),
                                   "Clear PFP", self.label_font)
        self._thumb_cache: dict[str, pygame.Surface] = {}

    def _pfp_thumbs(self) -> list[tuple[str, pygame.Rect]]:
        out = []
        x0, y0 = self.MARGIN_X, self.top + 465
        for i, fname in enumerate(Account.list_pfps()[:14]):
            out.append((fname, pygame.Rect(x0 + i * 96, y0, 80, 80)))
        return out

    def _pick_and_upload_pfp(self) -> None:
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = tkinter.filedialog.askopenfilename(
            title="Select Profile Picture (.png)",
            filetypes=[("PNG images", "*.png")],
        )
        root.destroy()
        if not path:
            return
        saved = self.app.account.upload_pfp(path)
        if saved:
            self._thumb_cache.clear()
            self.status = f"Saved PFP: {saved}"
        else:
            self.status = "Invalid PNG file."

    def update(self, dt: float) -> None:
        pass

    def handle_event(self, event: pygame.event.Event, mouse: pygame.Vector2) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.editing_name = self.input_rect.collidepoint(mouse)
            if self.save_button.hit(mouse):
                self.app.account.set_name(self.name_input)
                self.name_input = self.app.account.name
                self.status = f"Saved name: {self.app.account.name}"
                self.editing_name = False
            elif self.upload_button.hit(mouse):
                self._pick_and_upload_pfp()
            elif self.clear_button.hit(mouse):
                self.app.account.set_pfp(None)
                self.status = "Cleared PFP."
            else:
                for fname, rect in self._pfp_thumbs():
                    if rect.collidepoint(mouse):
                        self.app.account.set_pfp(fname)
                        self.status = f"Selected PFP: {fname}"
                        break
        elif self.editing_name and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.app.account.set_name(self.name_input)
                self.name_input = self.app.account.name
                self.editing_name = False
                self.status = f"Saved name: {self.app.account.name}"
            elif event.key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
            elif event.unicode and event.unicode.isprintable() and len(self.name_input) < 18:
                self.name_input += event.unicode

    def draw(self, surface: pygame.Surface, mouse: pygame.Vector2) -> None:
        title = self.title_font.render("SETTINGS", True, (255, 255, 255))
        surface.blit(title, (self.MARGIN_X, self.top + 32))

        lbl = self.label_font.render("Player Name", True, (200, 205, 220))
        surface.blit(lbl, (self.MARGIN_X, self.top + 105))
        pygame.draw.rect(surface, (28, 34, 52), self.input_rect, border_radius=8)
        border_col = (255, 210, 80) if self.editing_name else (80, 90, 120)
        pygame.draw.rect(surface, border_col, self.input_rect, width=2, border_radius=8)
        name_surf = self.input_font.render(self.name_input + ("|" if self.editing_name else ""), True, (255, 255, 255))
        surface.blit(name_surf, name_surf.get_rect(midleft=(self.input_rect.left + 16, self.input_rect.centery)))
        self.save_button.draw(surface, mouse)

        pfp_lbl = self.label_font.render("Profile Picture (.png)", True, (200, 205, 220))
        surface.blit(pfp_lbl, (self.MARGIN_X, self.top + 245))
        preview = pygame.Rect(self.MARGIN_X, self.top + 290, 120, 120)
        pfp_img = self.app.account.load_pfp_surface((120, 120))
        if pfp_img is not None:
            surface.blit(pfp_img, preview)
        else:
            pygame.draw.rect(surface, self.app.account.player_color(), preview, border_radius=10)
        pygame.draw.rect(surface, (255, 210, 80), preview, width=3, border_radius=10)

        self.upload_button.draw(surface, mouse)
        self.clear_button.draw(surface, mouse)

        list_lbl = self.small_font.render(f"Uploaded in {PFP_DIR}:", True, (165, 170, 190))
        surface.blit(list_lbl, (self.MARGIN_X, self.top + 430))
        for fname, rect in self._pfp_thumbs():
            if fname not in self._thumb_cache:
                try:
                    raw = pygame.image.load(os.path.join(PFP_DIR, fname)).convert_alpha()
                    self._thumb_cache[fname] = pygame.transform.smoothscale(raw, (80, 80))
                except pygame.error:
                    continue
            surface.blit(self._thumb_cache[fname], rect)
            active = fname == self.app.account.pfp
            pygame.draw.rect(surface, (255, 210, 80) if active else (80, 90, 120),
                             rect, width=3 if active else 1, border_radius=6)

        if self.status:
            st = self.label_font.render(self.status, True, (255, 210, 80))
            surface.blit(st, (self.MARGIN_X, VIRTUAL_H - 90))
