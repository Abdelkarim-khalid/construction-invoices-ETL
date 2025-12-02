"""BOQ service - Business logic for BOQ management"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import BOQItem, Project
from app.schemas.boq import BOQItemCreate


def add_boq_item(
    db: Session,
    project_id: int,
    item: BOQItemCreate
) -> BOQItem:
    """
    إضافة بند BOQ جديد لمشروع
    
    Args:
        db: Database session
        project_id: معرّف المشروع
        item: بيانات البند الجديد
        
    Returns:
        BOQItem: البند المُضاف
        
    Raises:
        ValueError: إذا لم يتم العثور على المشروع
    """
    # التحقق من وجود المشروع
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"المشروع غير موجود (ID: {project_id})")
    
    new_item = BOQItem(
        project_id=project_id,
        item_code=item.item_code,
        description=item.description,
        unit=item.unit,
        unit_price=item.unit_price,
        is_partial=item.is_partial,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


def get_boq_items(db: Session, project_id: int) -> List[BOQItem]:
    """
    الحصول على بنود BOQ لمشروع
    
    Args:
        db: Database session
        project_id: معرّف المشروع
        
    Returns:
        List[BOQItem]: قائمة البنود
    """
    return db.query(BOQItem).filter(BOQItem.project_id == project_id).all()


def match_boq_item(
    db: Session,
    project_id: int,
    item_code: str
) -> Optional[BOQItem]:
    """
    البحث عن بند BOQ بالكود
    
    Args:
        db: Database session
        project_id: معرّف المشروع
        item_code: كود البند
        
    Returns:
        BOQItem | None: البند أو None إذا لم يتم العثور عليه
    """
    return (
        db.query(BOQItem)
        .filter(
            BOQItem.project_id == project_id,
            BOQItem.item_code == item_code,
        )
        .first()
    )
