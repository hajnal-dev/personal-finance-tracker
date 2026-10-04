"""Adatréteg: minden adatbázis-művelet itt van. Nem tud a felületről — se widget, se print."""
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session, selectinload
from modellek import engine, Tranzakcio, Kategoria


def kategoria_keres_vagy_letrehoz(session, nev):
    """Visszaadja a megadott nevű Kategoria objektumot; ha még nem létezik, létrehozza (commit nélkül)."""
    kategoria = session.scalars(
        select(Kategoria).where(Kategoria.nev == nev)
    ).first()

    if kategoria is None:
        kategoria = Kategoria(nev=nev)
        session.add(kategoria)

    return kategoria


def osszes_tranzakcio():
    """Visszaadja az összes tranzakciót, a kategóriáikkal együtt előre betöltve."""
    with Session(engine) as session:
        return session.scalars(
            select(Tranzakcio).options(selectinload(Tranzakcio.kategoria))
        ).all()


def uj_tranzakcio(datum, osszeg, tipus, kategoria_nev):
    """Elment egy új tranzakciót. Érvénytelen adatnál ValueError-t dob — a hívó dönti el, mit kezd vele."""
    with Session(engine) as session:
        kategoria = kategoria_keres_vagy_letrehoz(session, kategoria_nev)
        uj = Tranzakcio(datum=datum, osszeg=osszeg, tipus=tipus, kategoria=kategoria)
        session.add(uj)
        session.commit()


def tranzakcio_frissites(rekord_id, osszeg, tipus, kategoria_nev):
    """Módosít egy meglévő tranzakciót. Ha nem létezik, vagy az adat érvénytelen, ValueError-t dob."""
    with Session(engine) as session:
        tranzakcio = session.get(Tranzakcio, rekord_id)
        if tranzakcio is None:
            raise ValueError("A tranzakció nem található (lehet, hogy közben törölték).")

        tranzakcio.osszeg = osszeg        # itt fut a @validates; hiba esetén a ValueError kirepül, commit nélkül
        tranzakcio.tipus = tipus
        tranzakcio.kategoria = kategoria_keres_vagy_letrehoz(session, kategoria_nev)
        session.commit()


def tranzakcio_torles(rekord_id):
    """Törli a megadott azonosítójú tranzakciót. Ha nem létezik, ValueError-t dob."""
    with Session(engine) as session:
        tranzakcio = session.get(Tranzakcio, rekord_id)
        if tranzakcio is None:
            raise ValueError("A tranzakció nem található (lehet, hogy közben törölték).")

        session.delete(tranzakcio)         # megjelölés törlésre (még nem végleges)
        session.commit()                   # végleges törlés


def bevetel_kiadas_osszesen():
    """Visszaadja az összes bevétel és kiadás összegét, egy (bevetel, kiadas) párként."""
    with Session(engine) as session:
        # SELECT tipus, SUM(osszeg) FROM tranzakciok GROUP BY tipus
        sorok = session.execute(
            select(Tranzakcio.tipus, func.sum(Tranzakcio.osszeg))
            .group_by(Tranzakcio.tipus)
        ).all()

    osszegek = dict(sorok)             # pl. {"Bevétel": 6000.0, "Kiadás": 6000.0}
    # .get(kulcs, 0): ha egy típusból még nincs tranzakció, 0-t ad KeyError helyett
    return osszegek.get("Bevétel", 0), osszegek.get("Kiadás", 0)


def kategoriankenti_egyenleg():
    """Kategóriánként összesíti az összegeket (a kiadás negatív előjellel számít); (nev, osszeg) párok listáját adja."""
    # CASE WHEN tipus = 'Kiadás' THEN -osszeg ELSE osszeg END
    elojeles_osszeg = case(
        (Tranzakcio.tipus == "Kiadás", -Tranzakcio.osszeg),
        else_=Tranzakcio.osszeg,
    )

    with Session(engine) as session:
        return session.execute(
            select(Kategoria.nev, func.sum(elojeles_osszeg))
            .select_from(Tranzakcio)          # FROM tranzakciok
            .join(Tranzakcio.kategoria)       # JOIN kategoriak ON ... (a kapcsolatból tudja)
            .group_by(Kategoria.nev)
        ).all()