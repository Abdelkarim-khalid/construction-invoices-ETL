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
    TradeType,  # Enum: CIVIL / ELEC / MECH / GENERAL
)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _parse_float(value, default: float = 0.0) -> float:
    """يحول النصوص والأرقام إلى Float بشكل آمن"""
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
    """يفصل الوصف الأساسي عن المرحلة (النص بين القوسين)"""
    if text is None:
        return "", ""
    clean_text = str(text).strip()
    if not clean_text or clean_text.lower() == "nan":
        return "", ""

    pattern = r"\((.*?)\)$"
    match = re.search(pattern, clean_text)

    if match:
        phase = match.group(1).strip()
        main_desc = clean_text[: match.start()].strip()
        return main_desc, phase

    return clean_text, "كامل"


def _normalize_trade(trade: str | None) -> str:
    """
    يطبع قيمة التخصص لتكون واحدة من:
    CIVIL / ELEC / MECH / GENERAL
    ويقبل صيغ مختلفة (civil, كهرباء, ..)
    """
    if trade is None:
        return TradeType.GENERAL.value

    t = str(trade).strip().upper()

    # خرائط مرنة لبعض الصيغ المحتملة
    if t in ("CIVIL", "CIV", "مدني"):
        return TradeType.CIVIL.value
    if t in ("ELEC", "ELECT", "كهرباء"):
        return TradeType.ELEC.value
    if t in ("MECH", "MECHANICAL", "ميكانيكا", "ميكانيكى", "ميكانيكي"):
        return TradeType.MECH.value
    if t in ("GENERAL", "GEN", "عام"):
        return TradeType.GENERAL.value

    # لو جت قيمة أصلاً من الـ Enum نفسه
    # (يعني t = "CIVIL" أو "ELEC" ..)
    valid_values = [m.value for m in TradeType]
    if t in valid_values:
        return t

    raise ValueError(
        f"Invalid trade type '{trade}'. Allowed values: {valid_values}"
    )


# ---------------------------------------------------------
# رفع الإكسيل إلى Staging
# ---------------------------------------------------------

def process_excel_invoice(
    db: Session,
    project_id: int,
    file_path: str,
    inv_number: str | int,
    start_date: date,
    end_date: date,
    sheet_name: str | int = 0,
    trade_type: str = "GENERAL",  # التخصص (مدني/كهرباء/..)
):
    """
    قراءة ملف الإكسيل ورفع البيانات إلى منطقة Staging
    مع ربط كل صف بالتخصص (trade).
    لو المستخلص موجود (DRAFT) → يحذف فقط Staging الخاص بنفس التخصص ويعيد رفعه.
    """

    # 1) تحقق من المشروع
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project with id={project_id} not found")

    try:
        invoice_number_int = int(inv_number)
    except (TypeError, ValueError):
        raise ValueError("رقم المستخلص يجب أن يكون رقماً صحيحاً")

    # طباعة التخصص لصيغة موحدة (CIVIL/ELEC/..)
    normalized_trade = _normalize_trade(trade_type)

    # 2) هل المستخلص موجود؟
    existing_invoice = (
        db.query(InvoiceLog)
        .filter(
            InvoiceLog.project_id == project_id,
            InvoiceLog.invoice_number == invoice_number_int,
        )
        .first()
    )

    if existing_invoice:
        if existing_invoice.status == InvoiceStatus.APPROVED:
            raise ValueError(
                f"المستخلص رقم ({invoice_number_int}) معتمد سابقاً ولا يمكن التعديل عليه."
            )

        current_invoice_id = existing_invoice.id
        existing_invoice.period_start = start_date
        existing_invoice.period_end = end_date

        # حذف بيانات الـ Staging الخاصة بنفس التخصص فقط
        try:
            (
                db.query(StagingInvoiceDetail)
                .filter(
                    StagingInvoiceDetail.invoice_id == current_invoice_id,
                    StagingInvoiceDetail.trade == normalized_trade,
                )
                .delete()
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
    else:
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
        current_invoice_id = new_invoice.id

    # 3) قراءة الإكسيل
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        raise ValueError(f"فشل قراءة ملف الإكسيل: {str(e)}")

    # 4) Mapping الأعمدة
    col_map = {"item_code": None, "description": None, "qty": None, "percentage": None}
    lower_cols = {str(c).strip().lower(): c for c in df.columns}

    patterns_map = {
        "item_code": [
            "item_code",
            "code",
            "item",
            "boq",
            "boq_code",
            "رقم البند",
            "كود",
            "رقم بند",
            "بند",
        ],
        "description": [
            "description",
            "desc",
            "تفصيل",
            "البند",
            "بيان الأعمال",
            "وصف",
            "بنود الأعمال",
        ],
        "qty": [
            "total_qty",
            "qty",
            "quantity",
            "الكمية",
            "الكمية الحالية",
            "الجارى",
            "الجاري",
            "كمية الأعمال الجارية",
        ],
        "percentage": [
            "percentage",
            "pct",
            "نسبة",
            "نسبة الصرف",
            "نسبة التنفيذ",
        ],
    }

    for key, patterns in patterns_map.items():
        for p in patterns:
            lp = p.lower()
            if lp in lower_cols:
                col_map[key] = lower_cols[lp]
                break

    if not col_map["item_code"] or not col_map["qty"]:
        raise ValueError(
            f"الأعمدة المطلوبة (كود البند/الكمية) غير موجودة. الأعمدة المتاحة: {list(lower_cols.values())}"
        )

    # 5) إدخال إلى Staging
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
            invoice_id=current_invoice_id,
            row_index=int(idx),
            raw_item_code=str(raw_item_code).strip(),
            raw_description=str(raw_desc).strip() if pd.notna(raw_desc) else "",
            raw_qty=str(raw_qty).strip() if pd.notna(raw_qty) else "",
            raw_percentage=str(raw_pct).strip() if pd.notna(raw_pct) else "",
            trade=normalized_trade,  # ✅ تخزين التخصص بصيغة Enum value (CIVIL/ELEC/..)
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
        "invoice_id": current_invoice_id,
        "rows_staged": rows_staged,
        "trade": normalized_trade,
        "message": f"تم رفع {rows_staged} بند ({normalized_trade}) بنجاح للمسودة.",
    }


# ---------------------------------------------------------
# الاعتماد النهائي
# ---------------------------------------------------------

def approve_invoice(db: Session, invoice_id: int):
    """
    نقل البيانات من Staging إلى InvoiceDetail + DailyLedger
    مع مراعاة التخصص (trade) وربطه بالـ Enum TradeType
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

        # ✅ تطبيع التخصص قبل التخزين في Enum
        normalized_trade = _normalize_trade(getattr(s, "trade", None))

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
            trade=normalized_trade,  # هنا هتوصل للقيم: CIVIL/ELEC/MECH/GENERAL
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
        "errors": errors_found,
        "message": f"تم الاعتماد. بنجاح: {processed_count}، أخطاء: {errors_found}",
    }
