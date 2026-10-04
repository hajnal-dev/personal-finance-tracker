# - - - 0. Importálandók - - -
import tkinter as tk
import sqlite3
from tkinter import ttk
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from modellek import engine, Tranzakcio, Kategoria

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
    """Ellenőrzi és elmenti az új tranzakciót az adatbázisba (SQLAlchemy-vel), majd frissíti a listát és az egyenleget."""
    try:
        osszeg = float(osszeg_entry.get())
    except ValueError:
        print("Csak számot adj meg!")
        return

    kategoria_nev = kategoria_entry.get().strip() or "Egyéb"
    tipus = tipus_combo.get()
    datum = datetime.now().strftime("%Y-%m-%d")

    with Session(engine) as session:
        kategoria = kategoria_keres_vagy_letrehoz(session, kategoria_nev)

        try:
            # név szerinti paraméterek; a @validates itt, létrehozáskor ellenőrzi az összeget
            uj_tranzakcio = Tranzakcio(
                datum=datum,
                osszeg=osszeg,
                tipus=tipus,
                kategoria=kategoria,      # OBJEKTUM, nem id — az SQLAlchemy kitölti a kategoria_id-t
            )
        except ValueError as hiba:
            print(hiba)
            return                  # commit nélkül lépünk ki → semmi nem mentődik, az új kategória sem

        session.add(uj_tranzakcio)  # felvétel a nyilvántartásba
        session.commit()               # végleges mentés

    print("Sikeres mentés!")
    osszeg_entry.delete(0, tk.END)
    kategoria_entry.delete(0, tk.END)

    listazas()
    egyenleg()

listbox_objektum_terkep = {}


def kategoria_keres_vagy_letrehoz(session, nev):
    """Visszaadja a megadott nevű Kategoria objektumot; ha még nem létezik, létrehozza (commit nélkül)."""
    # SELECT ... FROM kategoriak WHERE nev = ? — csak most osztállyal és attribútummal
    kategoria = session.scalars(
        select(Kategoria).where(Kategoria.nev == nev)
    ).first()                       # első találat, vagy None, ha nincs ilyen

    if kategoria is None:
        kategoria = Kategoria(nev=nev)    # név szerinti paraméter!
        session.add(kategoria)            # felvétel a session nyilvántartásába (még nem mentés)

    return kategoria


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
    """A beviteli mezők adataival felülírja a korábban betöltött tranzakciót (SQLAlchemy-vel)."""
    if kijelolt_tranzakcio is None:
        return

    try:
        uj_osszeg = float(osszeg_entry.get())
    except ValueError:
        print("Csak számot adj meg!")
        return

    uj_kategoria_nev = kategoria_entry.get().strip() or "Egyéb"
    uj_tipus = tipus_combo.get()

    with Session(engine) as session:
        # 1. a módosítandó tranzakció betöltése EBBE a sessionbe, az elsődleges kulcsa alapján
        tranzakcio = session.get(Tranzakcio, kijelolt_tranzakcio.rekord_id)

        # 2. módosítás — az osszeg értékadásánál fut a @validates
        try:
            tranzakcio.osszeg = uj_osszeg
        except ValueError as hiba:
            print(hiba)
            return                      # commit nélkül kilépünk → semmi nem változik

        tranzakcio.tipus = uj_tipus
        tranzakcio.kategoria = kategoria_keres_vagy_letrehoz(session, uj_kategoria_nev)

        # 3. végleges mentés — add() nem kell, a session már követi az objektumot
        session.commit()

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