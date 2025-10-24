from .database import Base
from sqlalchemy import Column, String, DateTime, Float, Integer
from uuid import uuid4
from sqlalchemy.sql import func
from datetime import datetime, timezone


class Countries(Base):
    __tablename__ = "countries"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    capital = Column(String(100))
    region = Column(String(100))
    population = Column(Integer)
    currency_code = Column(String(100))
    exchange_rate= Column(Float)
    estimated_gdp = Column(Float)
    flag_url = Column(String(255))
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True)

class RefreshMeta(Base):
    __tablename__ = "refresh_meta"
    id = Column(Integer, primary_key=True)
    last_refreshed_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))


