from typing import List
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
import shutil
import os
import calendar

from database import get_db
import models
import schemas
from services.invoice_processor import process_excel_invoice, approve_invoice

app = FastAPI(title="Construction Cost Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "System is Running 🚀"}

# --- [تعديل ChatGPT الممتاز: عرض المشاريع] ---
@app.get("/projects/", response_model=List[schemas.ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).all()
    # تحويل بسيط للتأكد من التوافق
    return projects

@app.post("/projects/")
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    new_project = models.Project(
        name=project.name,
        location=project.location
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@app.post("/boq/{project_id}")
def add_boq_item(project_id: int, item: schemas.BOQItemCreate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_item = models.BOQItem(
        project_id=project_id,
        item_code=item.item_code,
        description=item.description,
        unit=item.unit,
        unit_price=item.unit_price,
        is_partial=item.is_partial,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.post("/upload-invoice/")
async def upload_invoice(
    project_id: int = Form(...),
    invoice_number: str = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    sheet_name: str = Form(...), 
    trade_type: str = Form("general"),  # <--- إضافة: استقبال التخصص
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    os.makedirs("temp_uploads", exist_ok=True)
    file_path = os.path.join("temp_uploads", file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # تحويل اسم الشيت لرقم لو أمكن
    final_sheet_name = sheet_name
    if str(sheet_name).isdigit():
        final_sheet_name = int(sheet_name)

    try:
        result = process_excel_invoice(
            db=db,
            project_id=project_id,
            file_path=file_path,
            inv_number=invoice_number,
            start_date=start_date,
            end_date=end_date,
            sheet_name=final_sheet_name,
            trade_type=trade_type,  # <--- تمرير التخصص للمعالج
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing invoice: {str(e)}")

    return result

@app.get("/invoices/{invoice_id}/staging")
def get_invoice_staging(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(models.InvoiceLog).filter(models.InvoiceLog.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    rows = []
    for s in invoice.staging_data:
        rows.append({
            "row_index": s.row_index,
            "raw_item_code": s.raw_item_code,
            "raw_description": s.raw_description,
            "raw_qty": s.raw_qty,
            "raw_percentage": s.raw_percentage,
            "is_valid": s.is_valid,
            "error_message": s.error_message,
        })
    return rows

@app.post("/invoices/{invoice_id}/approve")
def approve_invoice_endpoint(invoice_id: int, db: Session = Depends(get_db)):
    try:
        result = approve_invoice(db, invoice_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/reports/schedule/{project_id}")
def schedule_report(
    project_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db),
):
    import calendar
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")
    
    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    q = (
        db.query(
            models.BOQItem.item_code,
            models.BOQItem.description,
            func.sum(models.DailyLedger.distributed_qty).label("total_qty"),
        )
        .join(models.DailyLedger, models.DailyLedger.boq_item_id == models.BOQItem.id)
        .filter(
            models.DailyLedger.project_id == project_id,
            models.DailyLedger.entry_date >= start_date,
            models.DailyLedger.entry_date <= end_date,
        )
        .group_by(models.BOQItem.item_code, models.BOQItem.description)
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