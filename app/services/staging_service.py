"""Staging service - Business logic for managing staging data"""

from typing import List
from sqlalchemy.orm import Session

from app.models import StagingInvoiceDetail
from app.schemas.staging import StagingRowUpdate


def get_staging_rows(db: Session, invoice_id: int) -> List[StagingInvoiceDetail]:
    """
    الحصول على صفوف staging لمستخلص
    
    Args:
        db: Database session
        invoice_id: معرّف المستخلص
        
    Returns:
        List[StagingInvoiceDetail]: قائمة الصفوف
    """
    return (
        db.query(StagingInvoiceDetail)
        .filter(StagingInvoiceDetail.invoice_id == invoice_id)
        .order_by(StagingInvoiceDetail.row_index)
        .all()
    )


def update_staging_row(
    db: Session,
    row_id: int,
    updates: StagingRowUpdate
) -> StagingInvoiceDetail:
    """
    تعديل صف staging
    
    Args:
        db: Database session
        row_id: معرّف الصف
        updates: التحديثات المطلوبة
        
    Returns:
        StagingInvoiceDetail: الصف المُعدّل
        
    Raises:
        ValueError: إذا لم يتم العثور على الصف
    """
    row = db.query(StagingInvoiceDetail).filter(StagingInvoiceDetail.id == row_id).first()
    if not row:
        raise ValueError(f"الصف غير موجود (ID: {row_id})")
    
    # تطبيق التحديثات
    if updates.include_in_invoice is not None:
        row.include_in_invoice = updates.include_in_invoice
    if updates.raw_item_code is not None:
        row.raw_item_code = updates.raw_item_code
    if updates.raw_description is not None:
        row.raw_description = updates.raw_description
    if updates.raw_qty is not None:
        row.raw_qty = updates.raw_qty
    if updates.raw_percentage is not None:
        row.raw_percentage = updates.raw_percentage
    
    db.commit()
    db.refresh(row)
    return row


def update_staging_rows_bulk(
    db: Session,
    updates: List[StagingRowUpdate]
) -> int:
    """
    تعديل عدة صفوف staging دفعة واحدة
    
    Args:
        db: Database session
        updates: قائمة التحديثات
        
    Returns:
        int: عدد الصفوف المُعدّلة
    """
    updated_count = 0
    
    for update in updates:
        try:
            update_staging_row(db, update.id, update)
            updated_count += 1
        except ValueError:
            # تجاهل الصفوف غير الموجودة
            continue
    
    return updated_count
