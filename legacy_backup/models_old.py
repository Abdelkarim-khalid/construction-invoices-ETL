from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    Boolean,
    ForeignKey,
    Text,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base
import enum

# =========================================================
# 1. Enums
# =========================================================


class InvoiceStatus(enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"


class TradeType(enum.Enum):
    CIVIL = "CIVIL"       # مدني
    ELEC = "ELEC"         # كهرباء
    MECH = "MECH"         # ميكانيكا
    ARCH = "ARCH"         # معماري
    GENERAL = "GENERAL"   # عام


class RowType(enum.Enum):
    ITEM = "item"          # بند عادى يدخل المستخلص
    HEADER = "header"      # عنوان قسم
    TOTAL = "total"        # سطر إجمالى
    NOTE = "note"          # ملاحظات / شروحات
    SIGNATURE = "signature"  # توقيع / أسماء
    OTHER = "other"        # أى حاجة غير مصنفة


# =========================================================
# 2. Projects
# =========================================================


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)

    boq_items = relationship("BOQItem", back_populates="project")
    invoices = relationship("InvoiceLog", back_populates="project")
    ledger_entries = relationship("DailyLedger", back_populates="project")


# =========================================================
# 3. BOQ Items
# =========================================================


class BOQItem(Base):
    __tablename__ = "boq_items"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    item_code = Column(String, index=True)
    description = Column(String)
    unit = Column(String)
    unit_price = Column(Float, default=0.0)
    is_partial = Column(Boolean, default=False)

    project = relationship("Project", back_populates="boq_items")
    invoice_details = relationship("InvoiceDetail", back_populates="boq_item")
    ledger_entries = relationship("DailyLedger", back_populates="boq_item")


# =========================================================
# 4. Invoice Log
# =========================================================


class InvoiceLog(Base):
    __tablename__ = "invoices_log"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    invoice_number = Column(Integer, index=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    period_start = Column(Date)
    period_end = Column(Date)
    previous_invoice_id = Column(Integer, ForeignKey("invoices_log.id"), nullable=True)

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


# =========================================================
# 5. Staging Area
# =========================================================


class StagingInvoiceDetail(Base):
    __tablename__ = "staging_invoice_details"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices_log.id"))
    row_index = Column(Integer)

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

    invoice = relationship("InvoiceLog", back_populates="staging_data")


# =========================================================
# 6. Invoice Details
# =========================================================


class InvoiceDetail(Base):
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

    invoice = relationship("InvoiceLog", back_populates="details")
    boq_item = relationship("BOQItem", back_populates="invoice_details")


# =========================================================
# 7. Daily Ledger
# =========================================================


class DailyLedger(Base):
    __tablename__ = "daily_ledger"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    invoice_id = Column(Integer, ForeignKey("invoices_log.id"))
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"))
    entry_date = Column(Date, index=True)
    distributed_qty = Column(Float, default=0.0)

    project = relationship("Project", back_populates="ledger_entries")
    invoice = relationship("InvoiceLog", back_populates="ledger_entries")
    boq_item = relationship("BOQItem", back_populates="ledger_entries")
