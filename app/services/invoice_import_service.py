"""Invoice import service - Business logic for importing invoices from Excel"""

import pandas as pd
from datetime import date
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.models import InvoiceLog, StagingInvoiceDetail, Project, InvoiceStatus
from app.utils.parsing import normalize_trade
from app.utils.excel_reader import detect_columns, read_excel_to_dataframe


def get_or_create_invoice(
    db: Session,
    project_id: int,
    invoice_number: int,
    period_start: date,
    period_end: date,
) -> InvoiceLog:
    """
    الحصول على المستخلص أو إنشاءه إذا لم يكن موجوداً
    
    Args:
        db: Database session
        project_id: معرّف المشروع
        invoice_number: رقم المستخلص
        period_start: تاريخ البداية
        period_end: تاريخ النهاية
        
    Returns:
        InvoiceLog: المستخلص
        
    Raises:
        ValueError: إذا كان المستخلص معتمداً وغير قابل للتعديل
    """
    existing_invoice = (
        db.query(InvoiceLog)
        .filter(
            InvoiceLog.project_id == project_id,
            InvoiceLog.invoice_number == invoice_number,
        )
        .first()
    )

    if existing_invoice:
        if existing_invoice.status == InvoiceStatus.APPROVED:
            raise ValueError(
                f"المستخلص رقم ({invoice_number}) معتمد سابقاً ولا يمكن التعديل عليه."
            )
        
        # تحديث التواريخ
        existing_invoice.period_start = period_start
        existing_invoice.period_end = period_end
        db.commit()
        return existing_invoice
    
    # إنشاء مستخلص جديد
    new_invoice = InvoiceLog(
        project_id=project_id,
        invoice_number=invoice_number,
        period_start=period_start,
        period_end=period_end,
        status=InvoiceStatus.DRAFT,
    )
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)
    return new_invoice


def import_invoice_excel(
    db: Session,
    invoice_id: int,
    file_path: str,
    trade_type: str = "GENERAL",
    sheet_name: str | int = 0,
) -> Dict[str, Any]:
    """
    قراءة ملف Excel ورفع البيانات إلى Staging
    
    Args:
        db: Database session
        invoice_id: معرّف المستخلص
        file_path: مسار ملف Excel
        trade_type: نوع التخصص (CIVIL/ELEC/MECH/GENERAL)
        sheet_name: اسم أو رقم الورقة في Excel
        
    Returns:
        Dict: نتيجة العملية {status, rows_staged, trade, message}
        
    Raises:
        ValueError: في حالة حدوث أخطاء
    """
    # التحقق من وجود المستخلص
    invoice = db.query(InvoiceLog).filter(InvoiceLog.id == invoice_id).first()
    if not invoice:
        raise ValueError(f"المستخلص غير موجود (ID: {invoice_id})")
    
    # طباعة التخصص
    normalized_trade = normalize_trade(trade_type)
    
    # حذف بيانات Staging القديمة لنفس التخصص
    db.query(StagingInvoiceDetail).filter(
        StagingInvoiceDetail.invoice_id == invoice_id,
        StagingInvoiceDetail.trade == normalized_trade,
    ).delete()
    db.commit()
    
    # قراءة Excel
    df = read_excel_to_dataframe(file_path, sheet_name)
    
    # تحديد الأعمدة
    col_map = detect_columns(df)
    
    # إدخال البيانات إلى Staging
    staging_objects = []
    rows_staged = 0
    
    for idx, row in df.iterrows():
        raw_item_code = row.get(col_map["item_code"])
        
        # تجاهل الصفوف الفارغة
        if pd.isna(raw_item_code) or str(raw_item_code).strip() == "":
            continue
        
        raw_desc = row.get(col_map["description"])
        raw_qty = row.get(col_map["qty"])
        raw_pct = row.get(col_map["percentage"])
        
        staging_row = StagingInvoiceDetail(
            invoice_id=invoice_id,
            row_index=int(idx),
            raw_item_code=str(raw_item_code).strip(),
            raw_description=str(raw_desc).strip() if pd.notna(raw_desc) else "",
            raw_qty=str(raw_qty).strip() if pd.notna(raw_qty) else "",
            raw_percentage=str(raw_pct).strip() if pd.notna(raw_pct) else "",
            trade=normalized_trade,
            is_valid=False,
            error_message=None,
        )
        staging_objects.append(staging_row)
        rows_staged += 1
    
    if staging_objects:
        db.add_all(staging_objects)
        db.commit()
    
    return {
        "status": "staged",
        "invoice_id": invoice_id,
        "rows_staged": rows_staged,
        "trade": normalized_trade,
        "message": f"تم رفع {rows_staged} بند ({normalized_trade}) بنجاح للمسودة.",
    }
