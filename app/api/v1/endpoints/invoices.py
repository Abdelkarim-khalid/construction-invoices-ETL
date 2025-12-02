"""Invoices API endpoints"""

import os
import shutil
from typing import List
from datetime import date
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.config import settings
from app.schemas.staging import StagingRowRead, StagingRowUpdate
from app.services import (
    invoice_import_service,
    invoice_approval_service,
    staging_service,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/upload")
async def upload_invoice(
    project_id: int = Form(...),
    invoice_number: str = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    sheet_name: str = Form(...),
    trade_type: str = Form("general"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    رفع ملف Excel لمستخلص جديد
    """
    # حفظ الملف مؤقتاً
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # تحويل اسم الشيت لرقم لو أمكن
    final_sheet_name = sheet_name
    if str(sheet_name).isdigit():
        final_sheet_name = int(sheet_name)

    try:
        # تحويل رقم المستخلص
        invoice_number_int = int(invoice_number)
        
        # الحصول على المستخلص أو إنشاءه
        invoice = invoice_import_service.get_or_create_invoice(
            db=db,
            project_id=project_id,
            invoice_number=invoice_number_int,
            period_start=start_date,
            period_end=end_date,
        )
        
        # استيراد البيانات
        result = invoice_import_service.import_invoice_excel(
            db=db,
            invoice_id=invoice.id,
            file_path=file_path,
            trade_type=trade_type,
            sheet_name=final_sheet_name,
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error processing invoice: {str(e)}"
        )


@router.get("/{invoice_id}/staging", response_model=List[StagingRowRead])
def get_invoice_staging(invoice_id: int, db: Session = Depends(get_db)):
    """
    الحصول على بيانات staging لمستخلص
    """
    rows = staging_service.get_staging_rows(db, invoice_id)
    return rows


@router.put("/{invoice_id}/staging")
def update_staging_rows(
    invoice_id: int,
    updates: List[StagingRowUpdate],
    db: Session = Depends(get_db),
):
    """
    تعديل صفوف staging
    """
    try:
        updated_count = staging_service.update_staging_rows_bulk(db, updates)
        return {
            "status": "success",
            "updated_count": updated_count,
            "message": f"تم تحديث {updated_count} صف بنجاح"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{invoice_id}/approve")
def approve_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """
    اعتماد المستخلص ونقل البيانات من Staging إلى InvoiceDetail
    """
    try:
        result = invoice_approval_service.build_invoice_details_from_staging(
            db, invoice_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
