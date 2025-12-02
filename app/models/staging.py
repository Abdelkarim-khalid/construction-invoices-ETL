"""Staging area model for invoice import"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.enums import TradeType, RowType


class StagingInvoiceDetail(Base):
    """Model for staging invoice data before approval"""
    
    __tablename__ = "staging_invoice_details"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices_log.id"))
    row_index = Column(Integer)

    # Raw data from Excel
    raw_item_code = Column(String, nullable=True)
    raw_description = Column(String, nullable=True)
    raw_qty = Column(String, nullable=True)
    raw_percentage = Column(String, nullable=True)

    trade = Column(Enum(TradeType), default=TradeType.GENERAL)
    
    # نوع السطر (عنوان / بند / ملاحظة / إجمالى ..)
    row_type = Column(Enum(RowType), default=RowType.ITEM)

    # Soft delete: هل يدخل المستخلص ولا مستبعد يدويًا؟
    include_in_invoice = Column(Boolean, default=True)

    # صلاحية السطر بعد التفسير
    is_valid = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    invoice = relationship("InvoiceLog", back_populates="staging_data")
