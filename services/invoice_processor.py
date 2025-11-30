import pandas as pd
import re
from sqlalchemy.orm import Session
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
    """
    Helper: يحول أي قيمة نصية لرقم Float بأمان.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s or s.lower() == "nan":
        return default

    s = s.replace("%", "").strip()
    s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return default


def extract_phase_from_text(text: str):
    """
    يفصل الوصف عن المرحلة (ما بين القوسين)
    Input: "بند 9-2 باب (حلوق)" 
    Output: ("بند 9-2 باب", "حلوق")
    """
    if not text:
        return "", ""
    
    clean_text = str(text).strip()
    # البحث عن نص بين قوسين في نهاية السطر
    pattern = r"\((.*?)\)$"
    match = re.search(pattern, clean_text)
    
    if match:
        phase = match.group(1).strip()
        # نأخذ النص ما قبل القوس كوصف رئيسي (لو احتجناه)
        main_desc = clean_text[:match.start()].strip()
        return main_desc, phase
    
    return clean_text, "كامل"  # لو مفيش أقواس نعتبره بند كامل


def process_excel_invoice(
    db: Session,
    project_id: int,
    file_path: str,
    inv_number: str | int,
    start_date: date,
    end_date: date,
):
    """
    Phase 1: STAGING ONLY (الرفع المبدئي)
    """

    # تأكد إن المشروع موجود
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project with id={project_id} not found")

    try:
        invoice_number_int = int(inv_number)
    except (TypeError, ValueError):
        raise ValueError("invoice_number must be convertible to integer")

    # 1) إنشاء سجل المستخلص DRAFT
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

    # 2) قراءة ملف الإكسل
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        db.delete(new_invoice)
        db.commit()
        raise ValueError(f"Failed to read Excel file: {str(e)}")

    # Mapping للأعمدة
    col_map = {
        "item_code": None,
        "description": None,
        "qty": None,
        "percentage": None,
    }

    lower_cols = {str(c).strip().lower(): c for c in df.columns}

    patterns_map = {
        "item_code": ["item_code", "code", "item", "boq", "boq_code", "رقم البند", "كود"],
        "description": ["description", "desc", "تفصيل", "البند", "بيان الأعمال"],
        "qty": ["total_qty", "qty", "quantity", "الكمية", "الكمية الحالية"],
        "percentage": ["percentage", "pct", "نسبة", "نسبة الصرف"],
    }

    for key, patterns in patterns_map.items():
        for p in patterns:
            if p in lower_cols:
                col_map[key] = lower_cols[p]
                break

    if not col_map["item_code"] or not col_map["qty"]:
        # تنظيف لو فشل الرفع
        db.delete(new_invoice)
        db.commit()
        raise ValueError(
            f"Missing required columns (Item Code / Qty). Detected mapping: {col_map}"
        )

    # 3) تخزين الصفوف في Staging
    staging_objects = []
    rows_staged = 0
    
    for idx, row in df.iterrows():
        raw_item_code = row.get(col_map["item_code"])
        raw_description = row.get(col_map["description"]) if col_map["description"] else None
        raw_qty = row.get(col_map["qty"])
        raw_percentage = row.get(col_map["percentage"]) if col_map["percentage"] else None

        staging_row = StagingInvoiceDetail(
            invoice_id=new_invoice.id,
            row_index=int(idx),
            raw_item_code=str(raw_item_code).strip() if raw_item_code is not None else "",
            raw_description=str(raw_description).strip() if raw_description is not None else "",
            raw_qty=str(raw_qty).strip() if raw_qty is not None else "",
            raw_percentage=str(raw_percentage).strip() if raw_percentage is not None else "",
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
        "message": "Data uploaded to staging successfully. Please review and approve."
    }


def approve_invoice(db: Session, invoice_id: int):
    """
    Phase 2: APPROVAL & LEDGER (الاعتماد والحسابات)
    """

    invoice = db.query(InvoiceLog).filter(InvoiceLog.id == invoice_id).first()
    if not invoice:
        raise ValueError("Invoice not found")

    if invoice.status == InvoiceStatus.APPROVED:
        raise ValueError("Invoice is already approved")

    staging_rows = invoice.staging_data
    if not staging_rows:
        raise ValueError("No staging rows found for this invoice")

    # الفترة الزمنية للتوزيع
    start_date = invoice.period_start
    end_date = invoice.period_end
    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        raise ValueError("Invoice period must be at least 1 day")

    # تنظيف أي Ledger قديم لنفس المستخلص (لو بنعيد الاعتماد)
    db.query(DailyLedger).filter(DailyLedger.invoice_id == invoice.id).delete()
    # تنظيف أي Details قديمة لنفس المستخلص
    db.query(InvoiceDetail).filter(InvoiceDetail.invoice_id == invoice.id).delete()

    for s in staging_rows:
        raw_item_code = s.raw_item_code.strip() if s.raw_item_code else ""
        raw_desc = s.raw_description.strip() if s.raw_description else ""
        claimed_qty = _parse_float(s.raw_qty, default=0.0)
        current_percentage = _parse_float(s.raw_percentage, default=100.0)

        # 1. Validation Logic
        if not raw_item_code:
            s.is_valid = False
            s.error_message = "Missing item code"
            continue
            
        if claimed_qty == 0.0:
             # يمكن قبول كمية صفرية في بعض الحالات، لكن هنا سنعتبرها تحذير أو تجاهل
             # سنكمل ولكن نضع ملاحظة، أو نعتبرها Valid 
             pass

        # البحث عن البند في المقايسة
        boq_item = (
            db.query(BOQItem)
            .filter(
                BOQItem.project_id == invoice.project_id,
                BOQItem.item_code == raw_item_code,
            )
            .first()
        )
        
        if not boq_item:
            s.is_valid = False
            s.error_message = f"BOQ item code '{raw_item_code}' not found in project contract"
            continue

        # 2. Calculation Logic
        approved_qty = claimed_qty
        equivalent_qty = approved_qty * (current_percentage / 100.0)

        # 3. Cumulative Logic (التصحيح الهام)
        # نبحث عن آخر قيمة تراكمية لهذا البند في أي مستخلص سابق معتمد
        last_cumulative_record = (
            db.query(InvoiceDetail)
            .join(InvoiceLog)
            .filter(
                InvoiceLog.project_id == invoice.project_id,
                InvoiceLog.status == InvoiceStatus.APPROVED,
                InvoiceLog.id < invoice.id,  # مستخلصات سابقة فقط
                InvoiceDetail.boq_item_id == boq_item.id
            )
            .order_by(InvoiceLog.id.desc())  # الأحدث فالأحدث
            .first()
        )

        previous_cumulative_qty = 0.0
        if last_cumulative_record:
            previous_cumulative_qty = last_cumulative_record.total_cumulative_qty

        total_cumulative_qty = previous_cumulative_qty + equivalent_qty
        
        unit_price_at_time = boq_item.unit_price or 0.0
        total_value = equivalent_qty * unit_price_at_time

        # 4. Description Parsing (استخراج الأقواس)
        main_desc_text, phase_name = extract_phase_from_text(raw_desc)

        # إنشاء التفاصيل النهائية
        detail = InvoiceDetail(
            invoice_id=invoice.id,
            boq_item_id=boq_item.id,
            row_description=phase_name, # "حلوق" مثلاً
            current_percentage=current_percentage,
            claimed_qty=claimed_qty,
            approved_qty=approved_qty,
            equivalent_qty=equivalent_qty,
            previous_cumulative_qty=previous_cumulative_qty,
            total_cumulative_qty=total_cumulative_qty,
            unit_price_at_time=unit_price_at_time,
            total_value=total_value,
            notes=None,
        )
        db.add(detail)

        # 5. Daily Ledger Distribution (تفتيت الكمية)
        if equivalent_qty > 0:
            daily_rate = equivalent_qty / total_days
            # نستخدم Bulk Insert للسرعة هنا
            ledger_entries = []
            for i in range(total_days):
                current_day = start_date + timedelta(days=i)
                ledger_entry = DailyLedger(
                    project_id=invoice.project_id,
                    invoice_id=invoice.id,
                    boq_item_id=boq_item.id,
                    entry_date=current_day,
                    distributed_qty=daily_rate,
                )
                ledger_entries.append(ledger_entry)
            db.add_all(ledger_entries)

        # تحديث حالة الـ Staging
        s.is_valid = True
        s.error_message = "Processed Successfully"

    # تحديث حالة المستخلص
    invoice.status = InvoiceStatus.APPROVED
    
    # ربطه بالسابق (اختياري للـ Linked List)
    # يمكن تحديث previous_invoice_id هنا بناء على آخر مستخلص وجدناه
    
    db.commit()

    return {
        "status": "approved",
        "invoice_id": invoice.id,
        "message": "Invoice approved and ledger generated."
    }