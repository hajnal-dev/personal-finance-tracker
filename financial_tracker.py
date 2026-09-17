# - - - 0. Importálandók - - -
import tkinter as tk
import sqlite3
from tkinter import ttk
from datetime import datetime
from contextlib import contextmanager

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


# - - - 2. függvények - - -

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
    
    try:
        uj_tranzakcio = Tranzakcio(None, datum, osszeg, kategoria, tipus) #validáció a property-n keresztül
    except ValueError as hiba:
        print(hiba)
        return

    with db_kapcsolat() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO tranzakciok
        (osszeg, datum, kategoria, tipus)
        VALUES (?, ?, ?, ?)
        """, (osszeg, datum, kategoria, tipus))

    #nincs szükség conn.commit()-ra és conn.close()-ra
    #context manager automatikusan elintézi kilépéskor

    print("Sikeres mentés!")
    osszeg_entry.delete(0, tk.END)
    kategoria_entry.delete(0, tk.END)

    listazas()
    egyenleg()

listbox_objektum_terkep = {} 

# - - - Osztály - - -

class Tranzakcio:
    """Egy pénzügyi tranzakciót (bevételt vagy kiadást) reprezentál."""
    def __init__(self, rekord_id, datum, osszeg, kategoria, tipus): 
        self.rekord_id = rekord_id
        self.datum = datum
        self.osszeg = osszeg
        self.kategoria = kategoria
        self.tipus = tipus

    @property
    def osszeg(self):
        return self._osszeg

    @osszeg.setter
    def osszeg(self, uj_ertek):
        if uj_ertek < 0:
            raise ValueError("Negatív összeg nem adható meg!")
        else:
            self._osszeg = uj_ertek
            

    def __str__(self):
        if self.tipus == "Bevétel":
            jel = "+"
        else:
            jel = "-"

        return f"{self.rekord_id} {self.datum} {self.osszeg} ({self.kategoria}) ({self.tipus})" 


    def __repr__(self):
        return f"Tranzakcio(rekord_id={self.rekord_id}, osszeg={self.osszeg}, kategoria='{self.kategoria}')"


listbox_objektum_terkep = {}


def listazas():
    """Betölti az összes tranzakciót az adatbázisból, és megjeleníti a Listboxban."""
    tranzakcio_lista.delete(0, tk.END)
    listbox_objektum_terkep.clear()

    with db_kapcsolat() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tranzakciok")
        adatok = cursor.fetchall()

    for index, (rekord_id, datum, osszeg, kategoria, tipus) in enumerate(adatok):

        tranzakcio = Tranzakcio(rekord_id, datum, osszeg, kategoria, tipus)
        listbox_objektum_terkep[index] = tranzakcio
        tranzakcio_lista.insert(tk.END, tranzakcio)

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
        kategoria_entry.insert(0, tranzakcio.kategoria)
        tipus_combo.set(tranzakcio.tipus)

        listazas()
        egyenleg()


def frissites():
    """A beviteli mezőkben lévő (esetleg módosított) adatokkal felülírja a korábban kiválasztott tranzakciót az adatbázisban."""
    global kijelolt_tranzakcio

    if kijelolt_tranzakcio is None:
        return

    uj_osszeg = osszeg_entry.get()
    uj_kategoria = kategoria_entry.get()
    uj_tipus = tipus_combo.get()

    try:
        uj_osszeg = float(osszeg_entry.get())
        uj_tranzakcio = Tranzakcio(kijelolt_tranzakcio.rekord_id, kijelolt_tranzakcio.datum, uj_osszeg, uj_kategoria, uj_tipus)
    except ValueError as hiba:
        print(hiba)
        return

    with db_kapcsolat() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE tranzakciok
        SET osszeg = ?,
            kategoria = ?,
            tipus = ?
            WHERE rekord_id = ?
        """,
        (
            uj_osszeg,
            uj_kategoria,
            uj_tipus,
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
            SELECT osszeg, kategoria, tipus
            FROM tranzakciok
            """)
        adatok = cursor.fetchall()

    kategoriak = {}

    for osszeg, kategoria, tipus in adatok:

        if tipus == "Kiadás":
            osszeg = -osszeg

        if kategoria in kategoriak:
            kategoriak[kategoria] += osszeg
        else:
            kategoriak[kategoria] = osszeg 


    for kategoria, osszeg in kategoriak.items():
        print(f"{kategoria}: {osszeg:.0f} Ft")


# - - - 3. Ablak - - -

root = tk.Tk()
root.title("Pénzügyi Nyilvántartó")
root.geometry("400x510")

# - - - 4. GUI elemek - - -
with db_kapcsolat() as conn:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS tranzakciok(
        rekord_id INTEGER PRIMARY KEY,
        datum TEXT,
        osszeg REAL,
        kategoria TEXT,
        tipus TEXT
    )
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