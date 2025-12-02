"""Reports API endpoints"""

import calendar
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import BOQItem, DailyLedger

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/schedule/{project_id}")
def schedule_report(
    project_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db),
):
    """
    تقرير الجدول الزمني لمشروع في شهر معين
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")

    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    q = (
        db.query(
            BOQItem.item_code,
            BOQItem.description,
            func.sum(DailyLedger.distributed_qty).label("total_qty"),
        )
        .join(DailyLedger, DailyLedger.boq_item_id == BOQItem.id)
        .filter(
            DailyLedger.project_id == project_id,
            DailyLedger.entry_date >= start_date,
            DailyLedger.entry_date <= end_date,
        )
        .group_by(BOQItem.item_code, BOQItem.description)
        .all()
    )

    return [
        {
            "item_code": row.item_code,
            "description": row.description,
            "total_qty": float(row.total_qty) if row.total_qty is not None else 0.0,
        }
        for row in q
    ]
