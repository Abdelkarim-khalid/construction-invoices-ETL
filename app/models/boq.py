"""BOQ (Bill of Quantities) model"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class BOQItem(Base):
    """Model for BOQ items"""
    
    __tablename__ = "boq_items"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    item_code = Column(String, index=True)
    description = Column(String)
    unit = Column(String)
    unit_price = Column(Float, default=0.0)
    is_partial = Column(Boolean, default=False)

    # Relationships
    project = relationship("Project", back_populates="boq_items")
    invoice_details = relationship("InvoiceDetail", back_populates="boq_item")
    ledger_entries = relationship("DailyLedger", back_populates="boq_item")
