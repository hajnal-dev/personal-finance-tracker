# - - - Importálandók - - -
import pytest
from sqlalchemy import create_engine
import adatreteg


# - - - Fixture: friss teszt-adatbázis minden teszthez - - -
@pytest.fixture
def teszt_db(tmp_path, monkeypatch):
    """Minden teszthez új, üres adatbázist ad egy ideiglenes mappában — a penzugy.db-hez nem nyúl."""
    # tmp_path: a pytest által adott, tesztenként új ideiglenes mappa; a / operátor fájlútvonalat fűz hozzá
    teszt_engine = create_engine(f"sqlite:///{tmp_path / 'teszt.db'}")

    # az adatreteg modul SAJÁT "engine" nevét a teszt idejére a teszt-engine-re irányítjuk;
    # a teszt végén a monkeypatch automatikusan visszaállítja az eredetit
    monkeypatch.setattr(adatreteg, "engine", teszt_engine)

    # táblák + kezdő kategóriák létrehozása — már a TESZT-adatbázisban, mert az engine-t lecseréltük
    adatreteg.adatbazis_inicializalas()


# - - - Tesztek - - -

def test_uj_tranzakcio_megjelenik_a_listaban(teszt_db):
    """Egy elmentett tranzakció visszaolvasható, a megadott adatokkal és kategóriával."""
    adatreteg.uj_tranzakcio("2026-10-06", 2500.0, "Kiadás", "Étel")
    
    tranzakciok = adatreteg.osszes_tranzakcio()

    assert len(tranzakciok) == 1                       
    assert tranzakciok[0].osszeg == 2500.0             
    assert tranzakciok[0].kategoria.nev == "Étel"   


def test_bevetel_kiadas_osszesen(teszt_db):   
    """Egy bevétel és egy kiadás mentése után az összesítés a két összeget adja vissza."""

    adatreteg.uj_tranzakcio("2026-10-06", 10000.0, "Bevétel", "Teszt1")
    adatreteg.uj_tranzakcio("2026-10-06", 3000.0, "Kiadás", "Teszt2")

    bevetel, kiadas = adatreteg.bevetel_kiadas_osszesen()
    
    assert bevetel == 10000.0
    assert kiadas == 3000.0


def test_tranzakcio_torles(teszt_db):
    """Nem létező azonosító törtlésnél ValueError-t kell dobnia."""

    with pytest.raises(ValueError):
        adatreteg.tranzakcio_torles(666)

