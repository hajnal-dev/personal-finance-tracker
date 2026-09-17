# Pénzügyi Nyilvántartó

Személyes pénzügyi nyilvántartás bevétel és kiadások tekintetében.

## Funkciók

- **Bevétel és kiadás rögzítése** — Mentés gombbal, összeggel, szabadon
  megadható kategóriával, típussal (Bevétel / Kiadás); a dátum a
  rögzítéskor automatikusan eltárolódik.
- **Betöltés** — a már felvitt sor kijelölés után betölthető szerkesztésre.
- **Frissítés** — a betöltött tranzakció adatai módosíthatók, majd a
  Frissítés gombbal menthetők.
- **Kijelölt törlése** — egyesével törölhetők a tranzakciók.
- **Egyenleg** — a bevételek és kiadások különbsége automatikusan
  kiszámolódik és megjelenik.
- **Kategóriák** — kategóriánkénti összesítés (jelenleg konzolra kiírva).

## Használt technológiák

- Python 3
- Tkinter — a grafikus felülethez
- SQLite3 — az adattároláshoz

A program objektumorientált felépítésű: a tranzakciókat egy `Tranzakcio`
osztály reprezentálja, `@property`-vel validált összeg-mezővel.

## Futtatás
```
cd personal_finance_tracker
python financial_tracker.py
```

## Előfeltétel

Nincs külön telepítendő csomag — a `tkinter` és `sqlite3` a legtöbb Python
3-telepítéssel alapból érkezik.

## Screenshot

![Pénzügyi Nyilvántartó képernyőkép](screenshot.png)