"""Invoice models (InvoiceLog and InvoiceDetail)"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    ForeignKey,
    Text,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.enums import InvoiceStatus, TradeType


class InvoiceLog(Base):
    """Model for invoice header/log"""
    
    __tablename__ = "invoices_log"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    invoice_number = Column(Integer, index=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    period_start = Column(Date)
    period_end = Column(Date)
    previous_invoice_id = Column(Integer, ForeignKey("invoices_log.id"), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="invoices")
    details = relationship("InvoiceDetail", back_populates="invoice")
    staging_data = relationship("StagingInvoiceDetail", back_populates="invoice")
    ledger_entries = relationship("DailyLedger", back_populates="invoice")
    previous_invoice = relationship("InvoiceLog", remote_side=[id])

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "invoice_number",
            name="uix_project_invoice_number",
        ),
    )


class InvoiceDetail(Base):
    """Model for invoice line items/details"""
    
    __tablename__ = "invoice_details"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices_log.id"))
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"))

    row_description = Column(String, nullable=True)
    current_percentage = Column(Float, default=100.0)
    claimed_qty = Column(Float, default=0.0)
    approved_qty = Column(Float, default=0.0)
    equivalent_qty = Column(Float, default=0.0)

    previous_cumulative_qty = Column(Float, default=0.0)
    total_cumulative_qty = Column(Float, default=0.0)
    unit_price_at_time = Column(Float)
    total_value = Column(Float, default=0.0)
    notes = Column(Text)

    trade = Column(Enum(TradeType), default=TradeType.GENERAL)

    # Relationships
    invoice = relationship("InvoiceLog", back_populates="details")
    boq_item = relationship("BOQItem", back_populates="invoice_details")
