import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")

engine = None
SessionLocal = None

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Table 1: Stores the Form Data
class UserRecord(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    dob = Column(String)
    time = Column(String)
    location = Column(String)
    gender = Column(String)

    # Establishes a relationship to the reports table
    destiny_report = relationship("ReportRecord", back_populates="user", uselist=False)


# Table 2: Stores the Gemini AI Output
class ReportRecord(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    sun_sign = Column(String)
    career_tea = Column(String)
    love_gossip = Column(String)
    karmic_roast = Column(String)

    user = relationship("UserRecord", back_populates="destiny_report")


def init_db():
    if engine is None:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL or SUPABASE_DATABASE_URL in the environment."
        )
    Base.metadata.create_all(bind=engine)
