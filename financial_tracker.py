# - - - 0. Importálandók - - -
import tkinter as tk
import sqlite3
from tkinter import ttk
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from modellek import engine, Tranzakcio

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

def mentes():
    """Ellenőrzi és elmenti az új tranzakciót az adatbázisba, majd frissíti a listát és az egyenleget."""
    try:
        osszeg = float(osszeg_entry.get())
    except ValueError:
        print("Csak számot adj meg!")
        return
    
    kategoria = kategoria_entry.get().strip() or "Egyéb"
    tipus = tipus_combo.get()
    datum = datetime.now().strftime("%Y-%m-%d")

    with db_kapcsolat() as conn:
        cursor = conn.cursor()
        kategoria_id = kategoria_id_lekeres(conn, kategoria)
        try:
            uj_tranzakcio = Tranzakcio(None, datum, osszeg, kategoria, tipus, kategoria_id) #validáció a property-n keresztül
        except ValueError as hiba:
            print(hiba)
            return
        cursor.execute("""
        INSERT INTO tranzakciok
        (datum, osszeg, tipus, kategoria_id)
        VALUES (?, ?, ?, ?)
        """, (datum, osszeg, tipus, kategoria_id))

    
    print("Sikeres mentés!")
    osszeg_entry.delete(0, tk.END)
    kategoria_entry.delete(0, tk.END)

    listazas()
    egyenleg()

listbox_objektum_terkep = {} 


def kategoria_id_lekeres(conn, nev):
    """Visszaadja a megadott nevű kategória id-ját; ha még nem létezik, létrehozza."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM kategoriak WHERE nev = ?", (nev,))
    talalat = cursor.fetchone()

    if talalat:
        return talalat[0]
    else:
        cursor.execute("INSERT INTO kategoriak(nev) VALUES (?)", (nev,))
        return cursor.lastrowid


def listazas():
    """Betölti az összes tranzakciót az adatbázisból (SQLAlchemy-vel), és megjeleníti a Listboxban."""
    tranzakcio_lista.delete(0, tk.END)
    listbox_objektum_terkep.clear()

    with Session(engine) as session:
        # a listazas()-ban a lekérdezés:
        tranzakciok = session.scalars(
            select(Tranzakcio).options(selectinload(Tranzakcio.kategoria))   # melyik kapcsolatot töltse be előre?
        ).all()

        # a Listbox-feltöltés a with-en BELÜL marad: a str() itt hívja a __str__-t,
        # ami a self.kategoria.nev miatt még nyitott sessiont igényel
        for index, tranzakcio in enumerate(tranzakciok):
            listbox_objektum_terkep[index] = tranzakcio  #objektum mentése a térképbe az indexhez
            tranzakcio_lista.insert(tk.END, str(tranzakcio))

    egyenleg()


def torles():
    """Törli a Listboxban kijelölt tranzakciót az adatbázisból."""
    kijelolt = tranzakcio_lista.curselection() 

    if kijelolt:
        index = kijelolt[0] 
        tranzakcio = listbox_objektum_terkep[index]

        with db_kapcsolat() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            DELETE FROM tranzakciok
            WHERE rekord_id = ?
            """, (tranzakcio.rekord_id,))

        listazas()
        egyenleg()

        
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

        listazas()
        egyenleg()


def frissites():
    """A beviteli mezőkben lévő (esetleg módosított) adatokkal felülírja a korábban kiválasztott tranzakciót az adatbázisban."""
    global kijelolt_tranzakcio

    if kijelolt_tranzakcio is None:
        return

    uj_kategoria = kategoria_entry.get()
    uj_tipus = tipus_combo.get()


    with db_kapcsolat() as conn:
        cursor = conn.cursor()
        kategoria_id = kategoria_id_lekeres(conn, uj_kategoria)
        try:
            uj_osszeg = float(osszeg_entry.get())
            uj_tranzakcio = Tranzakcio(kijelolt_tranzakcio.rekord_id, kijelolt_tranzakcio.datum, uj_osszeg, uj_kategoria, uj_tipus, kategoria_id)
            #validáció a property-n keresztül
        except ValueError as hiba:
            print(hiba)
            return
        cursor.execute("""
        UPDATE tranzakciok
        SET osszeg = ?,
            tipus = ?,
            kategoria_id = ?
            WHERE rekord_id = ?
        """,
        (
            uj_osszeg,
            uj_tipus,
            kategoria_id,
            kijelolt_tranzakcio.rekord_id
            )
        )


    listazas()
    egyenleg()


def egyenleg():
    """Kiszámolja a bevételek és kiadások különbségét, és frissíti a bevétel/kiadás/egyenleg feliratokat."""
    with db_kapcsolat() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT osszeg, tipus
            FROM tranzakciok
            """)
        adatok = cursor.fetchall()

    bevetel = 0
    kiadas = 0

    for osszeg, tipus in adatok:

        if tipus == "Bevétel":
            bevetel += osszeg
        else:
            kiadas += osszeg
    
    bevetel_label.config(text=f"Bevétel: {bevetel} Ft")
    kiadas_label.config(text=f"Kiadás: {kiadas} Ft")
    egyenleg_label.config(text=f"Egyenleg: {bevetel - kiadas} Ft")


def kategoriak_osszesitese():
    """Kategóriánként összesíti a tranzakciók összegét, és konzolra kiírja az eredményt.
    Nem hoz létre semmit tartósan, csak a függvény futása alatt épül fel egy ideiglenes szótár."""
    with db_kapcsolat() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT k.nev, SUM(CASE WHEN t.tipus = 'Kiadás' THEN -t.osszeg ELSE t.osszeg END)
            FROM tranzakciok t
            JOIN  kategoriak k ON t.kategoria_id = k.id
            GROUP BY k.nev
            """)
        adatok = cursor.fetchall()

    for kategoria_nev, osszeg in adatok:
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