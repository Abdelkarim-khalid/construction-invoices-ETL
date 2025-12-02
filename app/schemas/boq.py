"""BOQ schemas"""

from pydantic import BaseModel


class BOQItemBase(BaseModel):
    """Base BOQ item schema"""
    item_code: str
    description: str
    unit: str
    unit_price: float
    is_partial: bool = False


class BOQItemCreate(BOQItemBase):
    """Schema for creating a BOQ item"""
    pass


class BOQItemRead(BOQItemBase):
    """Schema for reading a BOQ item"""
    id: int
    
    class Config:
        from_attributes = True
