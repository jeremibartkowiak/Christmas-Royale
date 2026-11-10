# Christmas Royale

Top-down 2D game (Python + Pygame-CE) with an absurd, meme-style Christmas theme.
This is the **boilerplate**: the technical foundation. All graphics are greybox placeholders (coloured rectangles) that can later be swapped for `.png` files.

## Uruchomienie

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

## Sterowanie

| Klawisz / przycisk | Akcja |
|---|---|
| W A S D | ruch |
| Mysz | celowanie |
| LPM | strzał (przytrzymanie = ogień ciągły dla broni automatycznych) |
| R | przeładowanie |
| 1 / 2 | wybór broni (Pistol / Sniper) |
| F11 | pełny ekran / okno |

## Co mamy

**Okno i kamera**
- Wymuszony DirectX (`SDL_RENDER_DRIVER = direct3d`).
- Wirtualny ekran 1920x1080, skalowany z zachowaniem proporcji (czarne pasy na 1920x1200, bez rozciągania tekstur).
- `Camera`: płynnie podąża za graczem po nieograniczonym świecie (tymczasowa siatka w tle).

**Obiekty świata**
- `GameObject`: baza (pozycja, greybox, `collidable`, opcjonalne `max_hp`, `name`).
- `Player`, `Bot`, `Obstacle` (ściany, skały) dziedziczą po `GameObject`.
- Kolizje: `move_and_collide()`, ruch w małych krokach osobno w osiach X i Y (ślizganie się po ścianach, bez przeskakiwania cienkich ścian).
- `NameTag`: napis nad postacią.

**Walka**
- `Gun`: nazwa, tryb automatyczny / półautomatyczny, szybkostrzelność, magazynek, czas przeładowania, obrażenia. Gotowe bronie: `make_pistol`, `make_sniper`.
- Hitscan: `raycast()` zwraca najbliższy trafiony obiekt, `Tracer` rysuje linię strzału.
- `Inventory`: plecak z wieloma broniami, każda trzyma własną amunicję.
- `Health`: komponent HP (gracz, boty, niszczalne obiekty). Obiekt z 0 HP znika (bot) lub eliminuje gracza.
- `Bot` może mieć broń: Bot4 strzela cały czas w jedną stronę (test śmierci gracza).

**Interfejs**
- HUD: amunicja i nazwa broni (prawy dolny róg), pasek HP w stylu Fortnite (lewy dolny róg).
- `KillFeed`: log eliminacji w prawym górnym rogu w formacie `zabójca  broń  ofiara`.
- Ekran `YOU HAVE BEEN ELIMINATED` z przyciskami `Respawn` i `Quit`.

## Struktura

Cały kod jest teraz w jednym pliku `main.py`. Podział na moduły jest do ustalenia.

## Do ustalenia (decyzje projektowe)

- Wszystkie liczby (obrażenia, szybkostrzelność, rozmiary, kolory, pozycje botów) to wartości tymczasowe.
- Czy zabite boty wracają po respawnie gracza.
- Struktura plików projektu.
- Pierwszy tryb gry do zrobienia (Deathmatch / Battle Royale / PvE / skrzynki).
