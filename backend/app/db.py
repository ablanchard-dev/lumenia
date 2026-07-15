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
