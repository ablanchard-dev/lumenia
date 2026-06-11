from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, Integer, DateTime, Boolean, func
from typing import Optional

class Base(DeclarativeBase):
    pass

class KV(Base):
    __allow_unmapped__ = True
    __tablename__ = "kv_store"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text)

class Profile(Base):
    __allow_unmapped__ = True
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    low_stim: Mapped[bool] = mapped_column(Boolean, default=True)
    font_size: Mapped[int] = mapped_column(Integer, default=16)
    pacing: Mapped[str] = mapped_column(String(32), default="normal")
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

class Journal(Base):
    __allow_unmapped__ = True
    __tablename__ = "journal"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

class Assessment(Base):
    __allow_unmapped__ = True
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[str] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer)
    severity: Mapped[Optional[str]] = mapped_column(String(32))
    risk_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())
