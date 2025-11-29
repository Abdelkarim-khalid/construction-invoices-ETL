from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import date

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    boq_items = relationship("BOQItem", back_populates="project")
    invoices = relationship("InvoiceLog", back_populates="project")

class BOQItem(Base):
    __tablename__ = 'boq_items'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    item_code = Column(String, index=True)
    description = Column(String)
    unit_price = Column(Float, default=0.0)
    is_partial = Column(Boolean, default=False)
    
    project = relationship("Project", back_populates="boq_items")
    invoice_details = relationship("InvoiceDetail", back_populates="boq_item")

class InvoiceLog(Base):
    __tablename__ = 'invoices_log'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    invoice_number = Column(String)
    file_name = Column(String, unique=True)
    period_start = Column(Date)
    period_end = Column(Date)
    
    project = relationship("Project", back_populates="invoices")
    details = relationship("InvoiceDetail", back_populates="invoice")

class InvoiceDetail(Base):
    __tablename__ = 'invoice_details'
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey('invoices_log.id'))
    boq_item_id = Column(Integer, ForeignKey('boq_items.id'))
    
    row_description = Column(String) # (حلوق، ضلف...)
    completion_pct = Column(Float)   # نسبة الصرف
    
    previous_qty = Column(Float, default=0.0)
    current_qty = Column(Float, default=0.0)  # Delta (كمية الشهر ده)
    total_qty = Column(Float, default=0.0)    # Cumulative (تراكمي)
    
    total_value_gross = Column(Float, default=0.0)
    total_value_net = Column(Float, default=0.0)
    
    invoice = relationship("InvoiceLog", back_populates="details")
    boq_item = relationship("BOQItem", back_populates="invoice_details")

class DailyLedger(Base):
    __tablename__ = 'daily_ledger'
    id = Column(Integer, primary_key=True, index=True)
    entry_date = Column(Date, index=True)
    boq_item_id = Column(Integer, ForeignKey('boq_items.id'))
    source_invoice_id = Column(Integer, ForeignKey('invoices_log.id'))
    daily_qty = Column(Float)
