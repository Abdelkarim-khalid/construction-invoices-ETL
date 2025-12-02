"""Excel reading and column detection utilities"""

import pandas as pd
from typing import Dict, Optional, Any


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    تحديد mapping الأعمدة من DataFrame
    
    Args:
        df: DataFrame المراد تحليله
        
    Returns:
        Dict: mapping الأعمدة {field_name: column_name}
        
    Raises:
        ValueError: إذا لم يتم العثور على الأعمدة المطلوبة
    """
    col_map = {
        "item_code": None,
        "description": None,
        "qty": None,
        "percentage": None
    }
    
    # تحويل أسماء الأعمدة إلى lowercase للمقارنة
    lower_cols = {str(c).strip().lower(): c for c in df.columns}

    # أنماط البحث لكل عمود
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

    # البحث عن كل عمود
    for key, patterns in patterns_map.items():
        for p in patterns:
            lp = p.lower()
            if lp in lower_cols:
                col_map[key] = lower_cols[lp]
                break

    # التحقق من وجود الأعمدة الأساسية
    if not col_map["item_code"] or not col_map["qty"]:
        raise ValueError(
            f"الأعمدة المطلوبة (كود البند/الكمية) غير موجودة. "
            f"الأعمدة المتاحة: {list(df.columns)}"
        )

    return col_map


def read_excel_to_dataframe(
    file_path: str,
    sheet_name: str | int = 0
) -> pd.DataFrame:
    """
    قراءة ملف Excel إلى DataFrame مع معالجة الأخطاء
    
    Args:
        file_path: مسار ملف Excel
        sheet_name: اسم أو رقم الورقة
        
    Returns:
        pd.DataFrame: البيانات المقروءة
        
    Raises:
        ValueError: في حالة فشل القراءة
    """
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        return df
    except FileNotFoundError:
        raise ValueError(f"الملف غير موجود: {file_path}")
    except Exception as e:
        raise ValueError(f"فشل قراءة ملف Excel: {str(e)}")
