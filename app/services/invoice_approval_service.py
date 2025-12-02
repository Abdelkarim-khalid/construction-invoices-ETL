"""Invoice approval service - Business logic for approving invoices"""

from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any

from app.models import (
    InvoiceLog,
    InvoiceDetail,
    DailyLedger,
    StagingInvoiceDetail,
    BOQItem,
    InvoiceStatus,
)
from app.utils.parsing import parse_float, extract_phase_from_text, normalize_trade


def build_invoice_details_from_staging(
    db: Session,
    invoice_id: int
) -> Dict[str, Any]:
    """
    نقل البيانات من Staging إلى InvoiceDetail + DailyLedger
    
    Args:
        db: Database session
        invoice_id: معرّف المستخلص
        
    Returns:
        Dict: نتيجة العملية {status, processed_items, errors, message}
        
    Raises:
        ValueError: في حالة حدوث أخطاء
    """
    invoice = db.query(InvoiceLog).filter(InvoiceLog.id == invoice_id).first()
    if not invoice:
        raise ValueError("المستخلص غير موجود")

    if invoice.status == InvoiceStatus.APPROVED:
        raise ValueError("المستخلص معتمد بالفعل")

    staging_rows = invoice.staging_data
    if not staging_rows:
        raise ValueError("لا توجد بيانات للمراجعة")

    start_date = invoice.period_start
    end_date = invoice.period_end
    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        total_days = 1

    # مسح تفاصيل المستخلص القديم بالكامل (قبل إعادة البناء)
    db.query(DailyLedger).filter(DailyLedger.invoice_id == invoice.id).delete()
    db.query(InvoiceDetail).filter(InvoiceDetail.invoice_id == invoice.id).delete()

    processed_count = 0
    errors_found = 0

    for s in staging_rows:
        s.is_valid = False
        s.error_message = None

        raw_item_code = (s.raw_item_code or "").strip()
        if not raw_item_code:
            s.error_message = "كود البند فارغ"
            errors_found += 1
            continue

        boq_item = (
            db.query(BOQItem)
            .filter(
                BOQItem.project_id == invoice.project_id,
                BOQItem.item_code == raw_item_code,
            )
            .first()
        )

        if not boq_item:
            s.error_message = f"كود البند '{raw_item_code}' غير موجود بالمقايسة"
            errors_found += 1
            continue

        claimed_qty = parse_float(s.raw_qty, 0.0)
        current_percentage = parse_float(s.raw_percentage, 100.0)
        approved_qty = claimed_qty
        equivalent_qty = approved_qty * (current_percentage / 100.0)

        last_cumulative_record = (
            db.query(InvoiceDetail)
            .join(InvoiceLog)
            .filter(
                InvoiceLog.project_id == invoice.project_id,
                InvoiceLog.status == InvoiceStatus.APPROVED,
                InvoiceLog.id < invoice.id,
                InvoiceDetail.boq_item_id == boq_item.id,
            )
            .order_by(desc(InvoiceLog.id))
            .first()
        )

        previous_cumulative_qty = (
            last_cumulative_record.total_cumulative_qty
            if last_cumulative_record
            else 0.0
        )
        total_cumulative_qty = previous_cumulative_qty + equivalent_qty

        unit_price = boq_item.unit_price or 0.0
        total_value = equivalent_qty * unit_price

        main_desc_text, phase_name = extract_phase_from_text(s.raw_description)
        final_desc = phase_name or main_desc_text or "بند كامل"

        # تطبيع التخصص
        normalized_trade = normalize_trade(getattr(s, "trade", None))

        detail = InvoiceDetail(
            invoice_id=invoice.id,
            boq_item_id=boq_item.id,
            row_description=final_desc,
            current_percentage=current_percentage,
            claimed_qty=claimed_qty,
            approved_qty=approved_qty,
            equivalent_qty=equivalent_qty,
            previous_cumulative_qty=previous_cumulative_qty,
            total_cumulative_qty=total_cumulative_qty,
            unit_price_at_time=unit_price,
            total_value=total_value,
            trade=normalized_trade,
        )
        db.add(detail)

        # توزيع على DailyLedger
        if equivalent_qty != 0:
            distribute_to_ledger(
                db=db,
                project_id=invoice.project_id,
                invoice_id=invoice.id,
                boq_item_id=boq_item.id,
                equivalent_qty=equivalent_qty,
                start_date=start_date,
                total_days=total_days,
            )

        s.is_valid = True
        s.error_message = "Success"
        processed_count += 1

    invoice.status = InvoiceStatus.APPROVED
    db.commit()

    return {
        "status": "approved",
        "invoice_id": invoice.id,
        "processed_items": processed_count,
        "errors": errors_found,
        "message": f"تم الاعتماد. بنجاح: {processed_count}، أخطاء: {errors_found}",
    }


def distribute_to_ledger(
    db: Session,
    project_id: int,
    invoice_id: int,
    boq_item_id: int,
    equivalent_qty: float,
    start_date: date,
    total_days: int,
):
    """
    توزيع الكميات على DailyLedger
    
    Args:
        db: Database session
        project_id: معرّف المشروع
        invoice_id: معرّف المستخلص
        boq_item_id: معرّف بند BOQ
        equivalent_qty: الكمية الفعلية
        start_date: تاريخ البداية
        total_days: عدد الأيام
    """
    daily_rate = equivalent_qty / total_days
    
    ledger_entries = [
        DailyLedger(
            project_id=project_id,
            invoice_id=invoice_id,
            boq_item_id=boq_item_id,
            entry_date=start_date + timedelta(days=i),
            distributed_qty=daily_rate,
        )
        for i in range(total_days)
    ]
    
    db.add_all(ledger_entries)
