from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()

class FDRate(Base):
    __tablename__ = 'fd_rates'
    
    id = Column(Integer, primary_key=True)
    bank = Column(String(100), nullable=False)
    tenure_description = Column(String(100), nullable=False)
    min_days = Column(Integer)
    max_days = Column(Integer)
    regular_rate = Column(Float)
    senior_rate = Column(Float)
    category = Column(String(50))
    scraped_date = Column(DateTime, default=datetime.utcnow)
    region = Column(String(50))
    currency = Column(String(10))
    is_tax_saving = Column(Boolean, default=False)
    is_special_rate = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('bank', 'tenure_description', name='uix_bank_tenure'),
    )

# Create database engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 