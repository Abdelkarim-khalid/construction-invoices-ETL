import pandas as pd
import re
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date, timedelta

from models import (
    InvoiceLog,
    InvoiceDetail,
    BOQItem,
    DailyLedger,
    Project,
    InvoiceStatus,
    StagingInvoiceDetail,
)

def _parse_float(value, default: float = 0.0) -> float:
    """Helper: يحول أي قيمة نصية لرقم Float بأمان."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return default
    s = s.replace("%", "").strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return default

def extract_phase_from_text(text):
    """يفصل الوصف عن المرحلة (ما بين القوسين)."""
    if text is None: return "", ""
    clean_text = str(text).strip()
    if not clean_text or clean_text.lower() == 'nan': return "", ""

    pattern = r"\((.*?)\)$"
    match = re.search(pattern, clean_text)
    
    if match:
        phase = match.group(1).strip()
        main_desc = clean_text[:match.start()].strip()
        return main_desc, phase
    
    return clean_text, "كامل"

def process_excel_invoice(
    db: Session,
    project_id: int,
    file_path: str,
    inv_number: str | int,
    start_date: date,
    end_date: date,
    sheet_name: str = 0,
):
    """Phase 1: STAGING ONLY with Duplication Check"""
    
    # 1. Validation: Project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project with id={project_id} not found")

    try:
        invoice_number_int = int(inv_number)
    except (TypeError, ValueError):
        raise ValueError("invoice_number must be convertible to integer")

    # --- فحص التكرار (The New Logic) ---
    existing_invoice = db.query(InvoiceLog).filter(
        InvoiceLog.project_id == project_id,
        InvoiceLog.invoice_number == invoice_number_int
    ).first()

    if existing_invoice:
        if existing_invoice.status == InvoiceStatus.APPROVED:
            raise ValueError(
                f"تنبيه: المستخلص رقم ({invoice_number_int}) لهذا المشروع تم اعتماده سابقاً. لا يمكن رفعه مرة أخرى."
            )
        else:
            # لو Draft امسحه ونضف مكانه
            db.query(StagingInvoiceDetail).filter(StagingInvoiceDetail.invoice_id == existing_invoice.id).delete()
            db.delete(existing_invoice)
            db.commit()
    # -----------------------------------

    # 2. Create Draft Log
    new_invoice = InvoiceLog(
        project_id=project_id,
        invoice_number=invoice_number_int,
        period_start=start_date,
        period_end=end_date,
        status=InvoiceStatus.DRAFT,
    )
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    # 3. Read Excel
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        db.delete(new_invoice)
        db.commit()
        raise ValueError(f"Failed to read Excel file: {str(e)}")

    # 4. Column Mapping Strategy
    col_map = {"item_code": None, "description": None, "qty": None, "percentage": None}
    lower_cols = {str(c).strip().lower(): c for c in df.columns}

    patterns_map = {
        "item_code": ["item_code", "code", "item", "boq", "boq_code", "رقم البند", "كود", "رقم بند"],
        "description": ["description", "desc", "تفصيل", "البند", "بيان الأعمال", "وصف", "بنود الأعمال"],
        "qty": ["total_qty", "qty", "quantity", "الكمية", "الكمية الحالية", "الجارى", "الجاري", "كمية الأعمال الجارية"],
        "percentage": ["percentage", "pct", "نسبة", "نسبة الصرف", "نسبة التنفيذ"],
    }

    for key, patterns in patterns_map.items():
        for p in patterns:
            lp = p.lower()
            if lp in lower_cols:
                col_map[key] = lower_cols[lp]
                break

    if not col_map["item_code"] or not col_map["qty"]:
        db.delete(new_invoice)
        db.commit()
        raise ValueError(f"Missing required columns (Item Code / Qty). Detected: {col_map}")

    # 5. Bulk Insert into Staging
    staging_objects = []
    rows_staged = 0
    
    for idx, row in df.iterrows():
        raw_item_code = row.get(col_map["item_code"])
        raw_desc = row.get(col_map["description"])
        raw_qty = row.get(col_map["qty"])
        raw_pct = row.get(col_map["percentage"])

        staging_row = StagingInvoiceDetail(
            invoice_id=new_invoice.id,
            row_index=int(idx),
            raw_item_code=str(raw_item_code).strip() if pd.notna(raw_item_code) else "",
            raw_description=str(raw_desc).strip() if pd.notna(raw_desc) else "",
            raw_qty=str(raw_qty).strip() if pd.notna(raw_qty) else "",
            raw_percentage=str(raw_pct).strip() if pd.notna(raw_pct) else "",
            is_valid=False,
            error_message=None,
        )
        staging_objects.append(staging_row)
        rows_staged += 1

    db.add_all(staging_objects)
    db.commit()

    return {
        "status": "staged",
        "invoice_id": new_invoice.id,
        "rows_staged": rows_staged,
        "message": "Data staged successfully. Please review and approve."
    }

def approve_invoice(db: Session, invoice_id: int):
    """Phase 2: APPROVAL & LEDGER"""
    
    invoice = db.query(InvoiceLog).filter(InvoiceLog.id == invoice_id).first()
    if not invoice:
        raise ValueError("Invoice not found")

    if invoice.status == InvoiceStatus.APPROVED:
        raise ValueError("Invoice is already approved")

    staging_rows = invoice.staging_data
    if not staging_rows:
        raise ValueError("No staging rows found")

    # Time Calculation
    start_date = invoice.period_start
    end_date = invoice.period_end
    if not start_date or not end_date:
        raise ValueError("Invoice dates are missing")
        
    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        raise ValueError("Invalid invoice period")

    # Clean old data
    db.query(DailyLedger).filter(DailyLedger.invoice_id == invoice.id).delete()
    db.query(InvoiceDetail).filter(InvoiceDetail.invoice_id == invoice.id).delete()

    processed_count = 0

    for s in staging_rows:
        s.is_valid = False
        s.error_message = None

        raw_item_code = s.raw_item_code.strip()
        if not raw_item_code:
            s.error_message = "Missing item code"
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
            s.error_message = f"Item code '{raw_item_code}' not in BOQ"
            continue

        claimed_qty = _parse_float(s.raw_qty, 0.0)
        current_percentage = _parse_float(s.raw_percentage, 100.0)

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

        previous_cumulative_qty = last_cumulative_record.total_cumulative_qty if last_cumulative_record else 0.0
        total_cumulative_qty = previous_cumulative_qty + equivalent_qty
        
        unit_price = boq_item.unit_price or 0.0
        total_value = equivalent_qty * unit_price

        main_desc_text, phase_name = extract_phase_from_text(s.raw_description)
        final_desc = phase_name or main_desc_text or "بند كامل"

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
        )
        db.add(detail)

        if equivalent_qty != 0:
            daily_rate = equivalent_qty / total_days
            ledger_entries = [
                DailyLedger(
                    project_id=invoice.project_id,
                    invoice_id=invoice.id,
                    boq_item_id=boq_item.id,
                    entry_date=start_date + timedelta(days=i),
                    distributed_qty=daily_rate,
                )
                for i in range(total_days)
            ]
            db.add_all(ledger_entries)

        s.is_valid = True
        s.error_message = "Success"
        processed_count += 1

    invoice.status = InvoiceStatus.APPROVED
    db.commit()

    return {
        "status": "approved",
        "invoice_id": invoice.id,
        "processed_items": processed_count,
        "message": f"Approved successfully. {processed_count} items processed."
    }