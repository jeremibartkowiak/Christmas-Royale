"""Punktacja meczu: uczestnicy (gracz i boty) i ranking."""
from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class Participant:
    """Uczestnik meczu. Trwały między respawnami (obiekt postaci powstaje na nowo, punkty zostają)."""
    name: str
    color: tuple[int, int, int]  # placeholder zdjęcia gracza (później .png)
    is_player: bool = False
    points: int = 0
    pfp_surface: pygame.Surface | None = None


def ranking(participants: list[Participant]) -> list[Participant]:
    """Od najwyższego wyniku; remis zachowuje kolejność z listy uczestników."""
    return sorted(participants, key=lambda p: -p.points)
