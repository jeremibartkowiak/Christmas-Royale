"""Katalog przedmiotów, rzadkości w stylu CS:GO oraz skrzynek (Cases)."""
from __future__ import annotations

import random
from dataclasses import dataclass

# Rzadkość -> (etykieta, kolor ramki w stylu CS:GO, waga losowania ze skrzynki)
RARITIES: dict[str, tuple[str, tuple[int, int, int], float]] = {
    "common": ("Common", (130, 155, 195), 50.0),
    "rare": ("Rare", (75, 105, 255), 28.0),
    "epic": ("Epic", (145, 70, 255), 14.0),
    "legendary": ("Legendary", (225, 65, 200), 6.0),
    "mythic": ("Mythic", (255, 195, 50), 2.0),
}


@dataclass(frozen=True)
class ItemDef:
    id: str
    name: str
    kind: str  # "player_skin" | "weapon_skin" | "case"
    rarity: str  # klucz z RARITIES
    color: tuple[int, int, int]
    price: int | None = None  # cena w Tokens w sklepie (None = tylko ze skrzynki)
    weapon_name: str = ""  # dla weapon_skin: "Pistol" / "Sniper" / "Assault Rifle"
    case_pool: tuple[str, ...] = ()  # dla case: lista id możliwych dropów

    @property
    def rarity_label(self) -> str:
        return RARITIES[self.rarity][0]

    @property
    def rarity_color(self) -> tuple[int, int, int]:
        return RARITIES[self.rarity][1]


# Tymczasowa lista skinów i skrzynek (greybox bez .png, do decyzji Użytkownika)
ITEM_LIST: tuple[ItemDef, ...] = (
    # Skiny gracza (placeholder: kolor kwadratu gracza)
    ItemDef("skin_elf", "Elf Green", "player_skin", "common", (65, 195, 95), price=400),
    ItemDef("skin_candy", "Candy Cane", "player_skin", "rare", (230, 75, 95), price=900),
    ItemDef("skin_frost", "Frosty Cyan", "player_skin", "epic", (75, 215, 240), price=1800),
    ItemDef("skin_cranberry", "Sprite Cranberry", "player_skin", "legendary", (195, 30, 75)),
    ItemDef("skin_golden_santa", "Golden Santa", "player_skin", "mythic", (255, 210, 60)),

    # Skiny broni (placeholder: kolor prostokąta broni)
    ItemDef("pistol_mint", "Pistol | Mint", "weapon_skin", "common", (120, 230, 180), price=350, weapon_name="Pistol"),
    ItemDef("pistol_crimson", "Pistol | Crimson", "weapon_skin", "epic", (220, 55, 70), weapon_name="Pistol"),
    ItemDef("ar_arctic", "AK-47 | Arctic", "weapon_skin", "rare", (200, 225, 245), price=1000, weapon_name="AK-47"),
    ItemDef("ar_blaze", "AK-47 | Blaze", "weapon_skin", "legendary", (255, 120, 40), weapon_name="AK-47"),
    ItemDef("sniper_emerald", "Sniper | Emerald", "weapon_skin", "epic", (50, 200, 120), price=1600, weapon_name="Sniper"),
    ItemDef("sniper_asiimov", "Sniper | Asiimov", "weapon_skin", "mythic", (255, 145, 35), weapon_name="Sniper"),

    # Skrzynki (Case to też item!)
    ItemDef(
        "case_christmas", "Christmas Case", "case", "rare", (190, 55, 65), price=500,
        case_pool=("skin_elf", "pistol_mint", "skin_candy", "ar_arctic", "skin_frost", "ar_blaze", "skin_golden_santa"),
    ),
    ItemDef(
        "case_meme", "Meme Case", "case", "epic", (145, 70, 220), price=1000,
        case_pool=("pistol_mint", "ar_arctic", "pistol_crimson", "sniper_emerald", "skin_cranberry", "sniper_asiimov"),
    ),
)

ITEMS: dict[str, ItemDef] = {item.id: item for item in ITEM_LIST}
SHOP_ITEMS: list[ItemDef] = [item for item in ITEM_LIST if item.price is not None]


def roll_case_item(case_id: str) -> ItemDef:
    """Losuje przedmiot ze skrzynki zgodnie z wagami rzadkości."""
    case_def = ITEMS[case_id]
    pool = [ITEMS[item_id] for item_id in case_def.case_pool]
    weights = [RARITIES[item.rarity][2] for item in pool]
    return random.choices(pool, weights=weights, k=1)[0]
