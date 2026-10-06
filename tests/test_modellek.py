# tests/test_modellek.py
# - - - Importálandók - - -
import pytest
from modellek import Tranzakcio


# - - - @validates tesztek (adatbázis nélkül) - - -
# A Tranzakcio objektum létrehozása még NEM ír az adatbázisba —
# csak egy Python objektum jön létre, de a @validates már ilyenkor lefut.

def test_pozitiv_osszeg_beallithato():
    """Érvényes összegnél az objektum létrejön, és az összeg változatlanul bekerül."""
    tranzakcio = Tranzakcio(osszeg=1500.0)
    assert tranzakcio.osszeg == 1500.0

def test_negativ_osszeg_valueerrort_dob():
    """Negatív összegnél ValueError-nak kell kirepülnie."""
    with pytest.raises(ValueError):        # melyik kivételt várjuk?
        Tranzakcio(osszeg=-100)


def test_nulla_osszeg():
    """0 értékű összegnél az objektum létrejön, és az összeg változatlanul bekerül. A 0-ás összegű tranzakció is információ."""
    tranzakcio = Tranzakcio(osszeg=0.0)
    assert tranzakcio.osszeg == 0.0