"""Enumeration types for the application"""

import enum


class InvoiceStatus(enum.Enum):
    """حالة المستخلص"""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"


class TradeType(enum.Enum):
    """نوع التخصص/التجارة"""
    CIVIL = "CIVIL"       # مدني
    ELEC = "ELEC"         # كهرباء
    MECH = "MECH"         # ميكانيكا
    ARCH = "ARCH"         # معماري
    GENERAL = "GENERAL"   # عام


class RowType(enum.Enum):
    """نوع السطر في المستخلص"""
    ITEM = "item"          # بند عادى يدخل المستخلص
    HEADER = "header"      # عنوان قسم
    TOTAL = "total"        # سطر إجمالى
    NOTE = "note"          # ملاحظات / شروحات
    SIGNATURE = "signature"  # توقيع / أسماء
    OTHER = "other"        # أى حاجة غير مصنفة
