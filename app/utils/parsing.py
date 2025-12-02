"""Parsing utilities for invoice data processing"""

import re
from typing import Tuple

from app.models.enums import TradeType, RowType


def parse_float(value, default: float = 0.0) -> float:
    """
    يحول النصوص والأرقام إلى Float بشكل آمن
    
    Args:
        value: القيمة المراد تحويلها
        default: القيمة الافتراضية في حالة الفشل
        
    Returns:
        float: القيمة المحولة
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return default
    
    # إزالة علامة % والفواصل
    s = s.replace("%", "").strip().replace(",", "")
    
    try:
        return float(s)
    except ValueError:
        return default


def normalize_trade(trade: str | None) -> str:
    """
    يطبع قيمة التخصص لتكون واحدة من:
    CIVIL / ELEC / MECH / ARCH / GENERAL
    ويقبل صيغ مختلفة (civil, كهرباء, ..)
    
    Args:
        trade: نوع التخصص
        
    Returns:
        str: التخصص المطبّع (Enum value)
        
    Raises:
        ValueError: إذا كانت القيمة غير صالحة
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
    if t in ("ARCH", "ARCHITECTURE", "معماري", "معمارى"):
        return TradeType.ARCH.value
    if t in ("GENERAL", "GEN", "عام"):
        return TradeType.GENERAL.value

    # لو جت قيمة أصلاً من الـ Enum نفسه
    valid_values = [m.value for m in TradeType]
    if t in valid_values:
        return t

    raise ValueError(
        f"Invalid trade type '{trade}'. Allowed values: {valid_values}"
    )


def extract_phase_from_text(text: str | None) -> Tuple[str, str]:
    """
    يفصل الوصف الأساسي عن المرحلة (النص بين القوسين)
    
    Args:
        text: النص المراد تحليله
        
    Returns:
        Tuple[str, str]: (الوصف الأساسي, المرحلة)
    """
    if text is None:
        return "", ""
    
    clean_text = str(text).strip()
    if not clean_text or clean_text.lower() == "nan":
        return "", ""

    # البحث عن نص بين قوسين في نهاية السطر
    pattern = r"\((.*?)\)$"
    match = re.search(pattern, clean_text)

    if match:
        phase = match.group(1).strip()
        main_desc = clean_text[: match.start()].strip()
        return main_desc, phase

    return clean_text, "كامل"


def classify_row(
    raw_item_code: str | None,
    raw_description: str | None,
    raw_qty: str | None,
    raw_percentage: str | None,
) -> RowType:
    """
    يصنف نوع السطر في المستخلص (بند / عنوان / إجمالي / ملاحظة / إلخ)
    
    Args:
        raw_item_code: كود البند الخام
        raw_description: الوصف الخام
        raw_qty: الكمية الخام
        raw_percentage: النسبة الخام
        
    Returns:
        RowType: نوع السطر
    """
    # تنظيف القيم
    code = str(raw_item_code).strip().lower() if raw_item_code else ""
    desc = str(raw_description).strip().lower() if raw_description else ""
    qty = str(raw_qty).strip() if raw_qty else ""
    pct = str(raw_percentage).strip() if raw_percentage else ""
    
    # لو الكود فاضي أو nan
    if not code or code == "nan":
        # لو في وصف، ممكن يكون header أو note
        if desc and desc != "nan":
            # كلمات مفتاحية للعناوين
            header_keywords = ["فصل", "باب", "chapter", "section", "قسم", "بند"]
            if any(kw in desc for kw in header_keywords):
                return RowType.HEADER
            
            # كلمات مفتاحية للإجماليات
            total_keywords = ["إجمالي", "مجموع", "total", "sum", "الإجمالى"]
            if any(kw in desc for kw in total_keywords):
                return RowType.TOTAL
                
            # كلمات مفتاحية للتوقيعات
            signature_keywords = ["توقيع", "المهندس", "المدير", "signature", "signed"]
            if any(kw in desc for kw in signature_keywords):
                return RowType.SIGNATURE
            
            # غالباً note
            return RowType.NOTE
        
        # لو مافيش حاجة خالص
        return RowType.OTHER
    
    # لو في كود وكمية → غالباً ITEM
    qty_val = parse_float(qty, 0.0)
    if qty_val != 0.0:
        return RowType.ITEM
    
    # لو في كود بس مافيش كمية → ممكن header أو item بكمية صفر
    # نفترض إنه ITEM (المستخدم يقدر يعدّله في الـ staging)
    return RowType.ITEM
