
# AFRIFLOW/backend/app/models/models.py

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    businesses = relationship("Business", back_populates="owner", cascade="all, delete-orphan")

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sector = Column(String, nullable=True)
    currency = Column(String, default="FCFA")
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="businesses")
    transactions = relationship("Transaction", back_populates="business", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="business", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    business = relationship("Business", back_populates="transactions")

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    business = relationship("Business", back_populates="expenses")