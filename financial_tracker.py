# - - - 0. Importálandók - - -
import tkinter as tk
import sqlite3
from tkinter import ttk
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from modellek import engine, Tranzakcio, Kategoria
import adatreteg

# - - - 1. Adatbázis inicializálása induláskor - - -
#azért jobb ilyenkor mert egyszer jön létre az indításkor
#nem fut le minden gombnyomáskor
#különválasztja az alkalmazás indulási lépéseit a felhasználói műveletektől

@contextmanager
def db_kapcsolat():
    """Megnyitja és a végén lezárja az adatbázis-kapcsolatot; hiba esetén is garantáltan bezárja."""
    conn = sqlite3.connect("penzugy.db")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# - - - Függvények - - -

kijelolt_tranzakcio = None
listbox_objektum_terkep = {}


def listazas():
    """Megjeleníti az összes tranzakciót a Listboxban (az adatot az adatrétegtől kéri)."""
    tranzakcio_lista.delete(0, tk.END)
    listbox_objektum_terkep.clear()

    for index, tranzakcio in enumerate(adatreteg.osszes_tranzakcio()):
        listbox_objektum_terkep[index] = tranzakcio
        tranzakcio_lista.insert(tk.END, str(tranzakcio))

    egyenleg()


def mentes():
    """Beolvassa a mezőket, és az adatréteggel elmenteti az új tranzakciót."""
    try:
        osszeg = float(osszeg_entry.get())
    except ValueError:
        print("Csak számot adj meg!")
        return

    kategoria_nev = kategoria_entry.get().strip() or "Egyéb"
    tipus = tipus_combo.get()
    datum = datetime.now().strftime("%Y-%m-%d")

    try:
        adatreteg.uj_tranzakcio(datum, osszeg, tipus, kategoria_nev)
    except ValueError as hiba:          # az adatréteg jelzi a hibát, a felület dönti el, mit kezd vele
        print(hiba)
        return

    print("Sikeres mentés!")
    osszeg_entry.delete(0, tk.END)
    kategoria_entry.delete(0, tk.END)

    listazas()                          # az egyenleg()-et a listazas() már meghívja → itt nem kell külön


def torles():
    """Az adatréteggel törölteti a Listboxban kijelölt tranzakciót."""
    global kijelolt_tranzakcio

    kijelolt = tranzakcio_lista.curselection()
    if not kijelolt:                    # nincs kijelölés → nincs mit törölni
        return

    tranzakcio = listbox_objektum_terkep[kijelolt[0]]

    try:
        adatreteg.tranzakcio_torles(tranzakcio.rekord_id)
    except ValueError as hiba:
        print(hiba)
        return

    # ha épp a betöltött (szerkesztés alatt álló) tranzakciót töröltük, „felejtsük el”
    if kijelolt_tranzakcio is not None and kijelolt_tranzakcio.rekord_id == tranzakcio.rekord_id:
        kijelolt_tranzakcio = None

    listazas()

        
def betoltes():
    """A kijelölt tranzakció adatait beírja a beviteli mezőkbe szerkesztésre."""
    global kijelolt_tranzakcio

    kijelolt = tranzakcio_lista.curselection()

    if kijelolt:
        index = kijelolt[0]
        tranzakcio = listbox_objektum_terkep[index]

        kijelolt_tranzakcio = tranzakcio

        osszeg_entry.delete(0, tk.END)
        kategoria_entry.delete(0, tk.END)
        osszeg_entry.insert(0, tranzakcio.osszeg)
        kategoria_entry.insert(0, tranzakcio.kategoria.nev)
        tipus_combo.set(tranzakcio.tipus)


def frissites():
    """Beolvassa a mezőket, és az adatréteggel módosíttatja a betöltött tranzakciót."""
    if kijelolt_tranzakcio is None:
        return

    try:
        uj_osszeg = float(osszeg_entry.get())
    except ValueError:
        print("Csak számot adj meg!")
        return

    uj_kategoria_nev = kategoria_entry.get().strip() or "Egyéb"
    uj_tipus = tipus_combo.get()

    try:
        adatreteg.tranzakcio_frissites(kijelolt_tranzakcio.rekord_id, uj_osszeg, uj_tipus, uj_kategoria_nev)
    except ValueError as hiba:
        print(hiba)
        return

    listazas()
  

def egyenleg():
    """Lekéri az összesített bevételt és kiadást, és frissíti a feliratokat."""
    bevetel, kiadas = adatreteg.bevetel_kiadas_osszesen()

    bevetel_label.config(text=f"Bevétel: {bevetel} Ft")
    kiadas_label.config(text=f"Kiadás: {kiadas} Ft")
    egyenleg_label.config(text=f"Egyenleg: {bevetel - kiadas} Ft")


def kategoriak_osszesitese():
    """Kiírja a konzolra a kategóriánkénti egyenleget."""
    for kategoria_nev, osszeg in adatreteg.kategoriankenti_egyenleg():
        print(f"{kategoria_nev}: {osszeg:.0f} Ft")


# - - - 3. Ablak - - -

root = tk.Tk()
root.title("Pénzügyi Nyilvántartó")
root.geometry("400x510")

# - - - 4. GUI elemek - - -
with db_kapcsolat() as conn:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS kategoriak(
        id INTEGER PRIMARY KEY,
        nev TEXT NOT NULL UNIQUE
)
""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS tranzakciok(
        rekord_id INTEGER PRIMARY KEY,
        datum TEXT,
        osszeg REAL,
        tipus TEXT,
        kategoria_id INTEGER,
        FOREIGN KEY (kategoria_id) REFERENCES kategoriak(id)
)
""")

with db_kapcsolat() as conn:
    kezdo_kat = conn.execute("""
    INSERT OR IGNORE INTO kategoriak(nev) VALUES ('Étel'), ('Lakás'), ('Szórakozás')
""")


osszeg_label = tk.Label(root, text="Összeg:")
osszeg_label.pack()
osszeg_entry = tk.Entry(root)
osszeg_entry.pack()

kategoria_label = tk.Label(root, text="Kategória")
kategoria_label.pack()
kategoria_entry = tk.Entry(root)
kategoria_entry.pack()

tipus_label = tk.Label(root, text="Típus")
tipus_label.pack()

tipus_combo = ttk.Combobox( #legördülő menü
    root,
    values=["Bevétel", "Kiadás"]
)
tipus_combo.pack()

tipus_combo.current(0)  #alapértelmezett: Bevétel

button = tk.Button(
root,
text="Mentés",
command=mentes
)
button.pack() 

tranzakcio_lista = tk.Listbox(root, width=40)
tranzakcio_lista.pack()

#Betöltés gomb
betoltes_button = tk.Button(
    root,
    text="Betöltés",
    command=betoltes
)
betoltes_button.pack()

#Frissítés gomb
frissites_button = tk.Button(
    root,
    text="Frissítés",
    command=frissites
)

frissites_button.pack()

#Törlés gomb
torles_button = tk.Button( #új gomb létrehozása
    root,
    text="Kijelölt törlése", #gomb felirata
    command=torles #kattintáskor meghívott függvény
)
torles_button.pack()

#Egyenleg gomb - konzolra írja ki az egyenleget
egyenleg_button = tk.Button(
    root,
    text="Egyenleg",
    command=egyenleg
)

egyenleg_button.pack()

bevetel_label = tk.Label(root, text="Bevétel: 0 Ft")
bevetel_label.pack()

kiadas_label = tk.Label(root, text="Kiadás: 0 Ft")
kiadas_label.pack()

egyenleg_label = tk.Label(root, text="Egyenleg: 0 Ft")
egyenleg_label.pack()

#Kategóriák gomb
kategoriak_button = tk.Button(
    root,
    text="Kategóriák",
    command=kategoriak_osszesitese
)

kategoriak_button.pack()

# - - - 5. Main loop - - -

listazas()
root.mainloop()