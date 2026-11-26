"""Ładowanie i cache'owanie tekstur .png z automatycznym zachowaniem proporcji i fallbackiem."""
from __future__ import annotations

import os

import pygame

_IMAGE_CACHE: dict[tuple[str, tuple[int, int] | None, bool], pygame.Surface | None] = {}

# Ikony broni do KillFeedu i HUD-u (nazwa broni -> ścieżka do .png)
WEAPON_ICONS: dict[str, str] = {
    "AK-47": os.path.join("assets", "weapons", "icon_ak47.png"),
    "Glock-17": os.path.join("assets", "weapons", "icon_glock17.png"),
    "AWP": os.path.join("assets", "weapons", "icon_awp.png"),
    "Knife": os.path.join("assets", "weapons", "icon_knife.png"),
}


def load_image(path: str, max_size: tuple[int, int] | None = None,
               keep_aspect: bool = True) -> pygame.Surface | None:
    """Wczytuje plik .png z kanałem alfa. Jeśli plik nie istnieje, zwraca None (fallback na greybox)."""
    key = (path, max_size, keep_aspect)
    if key in _IMAGE_CACHE:
        return _IMAGE_CACHE[key]
    if not path or not os.path.isfile(path):
        _IMAGE_CACHE[key] = None
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
    except pygame.error:
        _IMAGE_CACHE[key] = None
        return None
    if max_size is not None:
        mw, mh = max_size
        if keep_aspect:
            iw, ih = img.get_size()
            scale = min(mw / max(1, iw), mh / max(1, ih))
            target = (max(1, round(iw * scale)), max(1, round(ih * scale)))
        else:
            target = (mw, mh)
        img = pygame.transform.smoothscale(img, target)
    _IMAGE_CACHE[key] = img
    return img


def get_weapon_icon(weapon_name: str, max_size: tuple[int, int]) -> pygame.Surface | None:
    path = WEAPON_ICONS.get(weapon_name)
    return load_image(path, max_size=max_size, keep_aspect=True) if path else None
