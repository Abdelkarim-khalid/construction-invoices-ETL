"""Invoice schemas"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import date

from app.schemas.common import InvoiceStatusEnum


class InvoiceDetailBase(BaseModel):
    """Base invoice detail schema"""
    boq_item_id: int
    row_description: Optional[str] = None
    current_percentage: float = 100.0
    claimed_qty: float = 0.0
    approved_qty: float = 0.0
    notes: Optional[str] = None


class InvoiceDetailRead(InvoiceDetailBase):
    """Schema for reading invoice detail"""
    id: int
    equivalent_qty: float
    previous_cumulative_qty: float
    total_cumulative_qty: float
    total_value: float
    
    class Config:
        from_attributes = True


class InvoiceLogBase(BaseModel):
    """Base invoice log schema"""
    project_id: int
    invoice_number: int
    period_start: date
    period_end: date
    status: InvoiceStatusEnum = InvoiceStatusEnum.DRAFT


class InvoiceLogCreate(InvoiceLogBase):
    """Schema for creating invoice log"""
    previous_invoice_id: Optional[int] = None


class InvoiceLogRead(InvoiceLogBase):
    """Schema for reading invoice log"""
    id: int
    details: List[InvoiceDetailRead] = []
    
    class Config:
        from_attributes = True
