# - - - Importálandók - - -
from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates


# - - - Alaposztály - - -
# Minden modell ebből öröklődik; az SQLAlchemy ezen keresztül "tartja számon",
# milyen táblák léteznek (Base.metadata)
class Base(DeclarativeBase):
    pass


# - - - Kategoria modell - - -
class Kategoria(Base):
    # a MEGLÉVŐ tábla neve a penzugy.db-ben — pontosan egyeznie kell!
    __tablename__ = "kategoriak"

    id: Mapped[int] = mapped_column(primary_key=True)
    # a múlt heti sémában ez NOT NULL UNIQUE volt — itt ugyanezt kell kifejezni
    nev: Mapped[str] = mapped_column(unique=True, nullable=False)

    # kapcsolat: EGY kategóriához TÖBB tranzakció tartozhat → ezért lista
    # a back_populates a MÁSIK osztály megfelelő attribútumának nevét adja meg
    tranzakciok: Mapped[list["Tranzakcio"]] = relationship(back_populates="kategoria")

    def __repr__(self):
        return f"Kategoria(id={self.id}, nev='{self.nev}')"


# - - - Tranzakcio modell - - -
class Tranzakcio(Base):
    __tablename__ = "tranzakciok"

    rekord_id: Mapped[int] = mapped_column(primary_key=True)
    datum: Mapped[str]
    osszeg: Mapped[float]
    tipus: Mapped[str]
    # idegen kulcs: "táblanév.oszlopnév" formában (tábla, NEM osztály!)
    kategoria_id: Mapped[int] = mapped_column(ForeignKey("kategoriak.id"))

    # kapcsolat a másik irányba: EGY tranzakció → EGY kategória (ezért nem lista)
    kategoria: Mapped["Kategoria"] = relationship(back_populates="tranzakciok")

    # a régi @property helyett — lásd lent, miért
    @validates("osszeg")
    def osszeg_ellenorzes(self, kulcs, ertek):
        # kulcs = a validált attribútum neve ("osszeg"), ertek = a beállítani kívánt érték
        # 1) ha negatív: ugyanazt a ValueError-t dobd, mint eddig
        # 2) ha rendben van: ___ (mit kell visszaadnia a függvénynek, hogy az érték beálljon?)
        if ertek < 0:
            raise ValueError("Negatív összeg nem adható meg!")
        return ertek

    def __str__(self):
        jel = "+" if self.tipus == "Bevétel" else "-"
        # a kategória nevét most JOIN nélkül, a kapcsolaton keresztül éred el:
        return f"{self.rekord_id} {self.datum} {jel}{self.osszeg} {self.kategoria.nev} {self.tipus}"

    def __repr__(self):
        return f"Tranzakcio(rekord_id={self.rekord_id}, osszeg={self.osszeg}, kategoria_id={self.kategoria_id})"


# - - - Próbafuttatás - - -
# csak akkor fut, ha EZT a fájlt indítod közvetlenül, importáláskor nem
if __name__ == "__main__":
    engine = create_engine("sqlite:///penzugy.db", echo=True)  # echo=True → kiírja a generált SQL-t
    Base.metadata.create_all(engine)