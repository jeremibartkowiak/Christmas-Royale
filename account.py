"""Zapis i odczyt stanu konta gracza (JSON w `data/accounts/`) oraz obsługa PFP w `uploads/pfps/`."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field

import pygame

from items import ITEMS
from settings import PLAYER_COLOR, PLAYER_NAME

ACCOUNTS_DIR = os.path.join("data", "accounts")
DEFAULT_ACCOUNT_PATH = os.path.join(ACCOUNTS_DIR, "account.json")
PFP_DIR = os.path.join("uploads", "pfps")
START_TOKENS = 1500  # tymczasowe saldo startowe do testów sklepu i skrzynek
MATCH_REWARD_TOKENS = 5000  # nagroda za ukończenie meczu


@dataclass
class Account:
    name: str = PLAYER_NAME
    tokens: int = START_TOKENS
    pfp: str | None = None  # nazwa pliku w `uploads/pfps/`
    items: list[str] = field(default_factory=lambda: ["case_christmas"])
    equipped_player_skin: str | None = None
    equipped_weapon_skins: dict[str, str] = field(default_factory=dict)
    path: str = DEFAULT_ACCOUNT_PATH

    def __post_init__(self) -> None:
        self._pfp_cache: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}

    @classmethod
    def load(cls, path: str = DEFAULT_ACCOUNT_PATH) -> Account:
        if not os.path.exists(path):
            acc = cls(path=path)
            acc.save()
            return acc
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            acc = cls(path=path)
            acc.save()
            return acc
        valid_items = [iid for iid in data.get("items", []) if iid in ITEMS]
        eq_player = data.get("equipped_player_skin")
        if eq_player not in valid_items:
            eq_player = None
        eq_weapons = {
            w: iid for w, iid in data.get("equipped_weapon_skins", {}).items()
            if iid in valid_items
        }
        return cls(
            name=str(data.get("name", PLAYER_NAME))[:18] or PLAYER_NAME,
            tokens=max(0, int(data.get("tokens", START_TOKENS))),
            pfp=data.get("pfp"),
            items=valid_items,
            equipped_player_skin=eq_player,
            equipped_weapon_skins=eq_weapons,
            path=path,
        )

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        payload = {
            "name": self.name,
            "tokens": self.tokens,
            "pfp": self.pfp,
            "items": self.items,
            "equipped_player_skin": self.equipped_player_skin,
            "equipped_weapon_skins": self.equipped_weapon_skins,
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    # --- waluta i zakupy ---
    def add_tokens(self, amount: int) -> None:
        self.tokens = max(0, self.tokens + amount)
        self.save()

    def buy_item(self, item_id: str) -> bool:
        item = ITEMS.get(item_id)
        if item is None or item.price is None or self.tokens < item.price:
            return False
        self.tokens -= item.price
        self.items.append(item_id)
        self.save()
        return True

    def open_case(self, case_id: str, won_item_id: str) -> bool:
        if case_id not in self.items or won_item_id not in ITEMS:
            return False
        self.items.remove(case_id)
        self.items.append(won_item_id)
        self.save()
        return True

    # --- skiny ---
    def is_equipped(self, item_id: str) -> bool:
        item = ITEMS.get(item_id)
        if item is None:
            return False
        if item.kind == "player_skin":
            return self.equipped_player_skin == item_id
        if item.kind == "weapon_skin":
            return self.equipped_weapon_skins.get(item.weapon_name) == item_id
        return False

    def toggle_equip(self, item_id: str) -> None:
        item = ITEMS.get(item_id)
        if item is None or item_id not in self.items:
            return
        if item.kind == "player_skin":
            self.equipped_player_skin = None if self.equipped_player_skin == item_id else item_id
            self.save()
        elif item.kind == "weapon_skin":
            if self.equipped_weapon_skins.get(item.weapon_name) == item_id:
                self.equipped_weapon_skins.pop(item.weapon_name, None)
            else:
                self.equipped_weapon_skins[item.weapon_name] = item_id
            self.save()

    def player_color(self) -> tuple[int, int, int]:
        if self.equipped_player_skin and self.equipped_player_skin in ITEMS:
            return ITEMS[self.equipped_player_skin].color
        return PLAYER_COLOR

    def weapon_color(self, weapon_name: str, default: tuple[int, int, int]) -> tuple[int, int, int]:
        iid = self.equipped_weapon_skins.get(weapon_name)
        if iid and iid in ITEMS:
            return ITEMS[iid].color
        return default

    # --- nazwa i profile picture (PNG) ---
    def set_name(self, new_name: str) -> None:
        cleaned = new_name.strip()[:18]
        if cleaned:
            self.name = cleaned
            self.save()

    @staticmethod
    def list_pfps() -> list[str]:
        if not os.path.isdir(PFP_DIR):
            return []
        return sorted(f for f in os.listdir(PFP_DIR) if f.lower().endswith(".png"))

    def upload_pfp(self, src_path: str) -> str | None:
        """Kopiuje plik .png do `uploads/pfps/` pod unikalną nazwą i ustawia go jako PFP."""
        if not src_path or not os.path.isfile(src_path):
            return None
        try:
            pygame.image.load(src_path)  # walidacja, czy to poprawny obrazek
        except pygame.error:
            return None
        os.makedirs(PFP_DIR, exist_ok=True)
        filename = f"pfp_{uuid.uuid4().hex[:12]}.png"
        dst_path = os.path.join(PFP_DIR, filename)
        shutil.copy2(src_path, dst_path)
        self.pfp = filename
        self._pfp_cache.clear()
        self.save()
        return filename

    def set_pfp(self, filename: str | None) -> None:
        self.pfp = filename
        self.save()

    def load_pfp_surface(self, size: tuple[int, int]) -> pygame.Surface | None:
        if not self.pfp:
            return None
        key = (self.pfp, size)
        if key in self._pfp_cache:
            return self._pfp_cache[key]
        full = os.path.join(PFP_DIR, self.pfp)
        if not os.path.isfile(full):
            return None
        try:
            img = pygame.image.load(full).convert_alpha()
            scaled = pygame.transform.smoothscale(img, size)
        except pygame.error:
            return None
        self._pfp_cache[key] = scaled
        return scaled
