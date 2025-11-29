from pydantic import BaseModel
from datetime import date

# لإنشاء مشروع جديد
class ProjectCreate(BaseModel):
    name: str

# لإنشاء بند مقايسة
class BOQItemCreate(BaseModel):
    item_code: str
    description: str
    unit_price: float
    is_partial: bool = False
