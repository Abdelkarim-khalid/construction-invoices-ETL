"""Daily ledger model for quantity distribution"""

from sqlalchemy import Column, Integer, Float, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyLedger(Base):
    """Model for daily quantity distribution ledger"""
    
    __tablename__ = "daily_ledger"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    invoice_id = Column(Integer, ForeignKey("invoices_log.id"))
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"))
    entry_date = Column(Date, index=True)
    distributed_qty = Column(Float, default=0.0)

    # Relationships
    project = relationship("Project", back_populates="ledger_entries")
    invoice = relationship("InvoiceLog", back_populates="ledger_entries")
    boq_item = relationship("BOQItem", back_populates="ledger_entries")
