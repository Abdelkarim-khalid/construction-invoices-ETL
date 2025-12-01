from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from enum import Enum

# Shared Enums
class InvoiceStatusEnum(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"

# ---------------------------------------
# 1. Projects & BOQ
# ---------------------------------------
class BOQItemBase(BaseModel):
    item_code: str
    description: str
    unit: str             # تمت الإضافة بناء على المراجعة
    unit_price: float
    is_partial: bool = False

class BOQItemCreate(BOQItemBase):
    pass

class BOQItemRead(BOQItemBase):
    id: int
    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    name: str
    location: Optional[str] = None  # تمت الإضافة بناء على المراجعة

class ProjectRead(ProjectCreate):
    id: int
    boq_items: List[BOQItemRead] = []
    class Config:
        from_attributes = True

# ---------------------------------------
# 2. Invoice Details
# ---------------------------------------
class InvoiceDetailBase(BaseModel):
    boq_item_id: int
    row_description: Optional[str] = None
    current_percentage: float = 100.0
    claimed_qty: float = 0.0
    approved_qty: float = 0.0
    notes: Optional[str] = None

class InvoiceDetailRead(InvoiceDetailBase):
    id: int
    equivalent_qty: float
    previous_cumulative_qty: float
    total_cumulative_qty: float
    total_value: float
    
    class Config:
        from_attributes = True

# ---------------------------------------
# 3. Invoice Log
# ---------------------------------------
class InvoiceLogBase(BaseModel):
    project_id: int
    invoice_number: int
    period_start: date
    period_end: date
    status: InvoiceStatusEnum = InvoiceStatusEnum.DRAFT

class InvoiceLogCreate(InvoiceLogBase):
    previous_invoice_id: Optional[int] = None

class InvoiceLogRead(InvoiceLogBase):
    id: int
    details: List[InvoiceDetailRead] = []

    class Config:
        from_attributes = True