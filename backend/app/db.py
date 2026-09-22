import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/lumenia.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# S'assurer que le dossier de la base SQLite existe (sinon "unable to open database file"
# sur un checkout vierge / en CI, ou le dossier data/ n'est pas versionne).
if DATABASE_URL.startswith("sqlite:///"):
    _db_path = DATABASE_URL[len("sqlite:///"):]
    _parent = os.path.dirname(_db_path)
    if _parent and _db_path != ":memory:":
        os.makedirs(_parent, exist_ok=True)

engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

def init_db():
    Base.metadata.create_all(engine)
    # 23/09/2026 — `create_all` n'ajoute pas une colonne a une table qui existe deja. Une base
    # d'avant le cloisonnement recoit `owner` ici ; ses lignes restent a NULL, donc ne sont
    # plus lues par PERSONNE : fermer par defaut, ne rien supprimer.
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in ("profiles", "journal", "assessments"):
            if "owner" not in {c["name"] for c in insp.get_columns(table)}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN owner VARCHAR(36)"))
