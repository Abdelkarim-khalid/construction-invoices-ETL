"""Staging schemas"""

from pydantic import BaseModel
from typing import Optional


class StagingRowRead(BaseModel):
    """Schema for reading staging row"""
    id: int
    row_index: int
    raw_item_code: Optional[str]
    raw_description: Optional[str]
    raw_qty: Optional[str]
    raw_percentage: Optional[str]
    trade: str
    row_type: str
    include_in_invoice: bool
    is_valid: bool
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class StagingRowUpdate(BaseModel):
    """Schema for updating staging row"""
    id: int
    include_in_invoice: Optional[bool] = None
    raw_item_code: Optional[str] = None
    raw_description: Optional[str] = None
    raw_qty: Optional[str] = None
    raw_percentage: Optional[str] = None
