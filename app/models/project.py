"""Project model"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Project(Base):
    """Model for construction projects"""
    
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)

    # Relationships
    boq_items = relationship("BOQItem", back_populates="project")
    invoices = relationship("InvoiceLog", back_populates="project")
    ledger_entries = relationship("DailyLedger", back_populates="project")
