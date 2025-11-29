from fastapi import FastAPI, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from services.invoice_processor import process_excel_invoice
from datetime import date
import shutil
import os

app = FastAPI(title="Construction Cost Control API")

# 1. Endpoint لإنشاء مشروع جديد
@app.post("/projects/")
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    new_project = models.Project(name=project.name)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

# 2. Endpoint لتعريف بنود المقايسة
@app.post("/boq/{project_id}")
def add_boq_item(project_id: int, item: schemas.BOQItemCreate, db: Session = Depends(get_db)):
    new_item = models.BOQItem(project_id=project_id, **item.dict())
    db.add(new_item)
    db.commit()
    return {"status": "Item Added", "code": item.item_code}

# 3. Endpoint رفع المستخلص (الأهم)
@app.post("/upload-invoice/")
async def upload_invoice(
    project_id: int = Form(...),
    invoice_number: str = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # حفظ الملف مؤقتاً
    temp_folder = "temp_uploads"
    os.makedirs(temp_folder, exist_ok=True)
    file_path = f"{temp_folder}/{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # استدعاء السيرفيس للمعالجة
    try:
        result = process_excel_invoice(
            db=db,
            project_id=project_id,
            file_path=file_path,
            inv_number=invoice_number,
            start_date=start_date,
            end_date=end_date
        )
        return result
    except Exception as e:
        return {"error": str(e)}

# 4. Endpoint تقرير البرنامج الزمني
@app.get("/reports/schedule/{project_id}")
def get_schedule_report(project_id: int, month: int, year: int, db: Session = Depends(get_db)):
    # كويري بسيط لتجميع الكميات لشهر معين
    # هذا مثال مبسط، يمكنك استخدام SQL أعقد
    from sqlalchemy import extract, func
    
    results = db.query(
        models.BOQItem.item_code, 
        func.sum(models.DailyLedger.daily_qty).label("total_monthly_qty")
    ).join(models.DailyLedger)\
     .filter(models.BOQItem.project_id == project_id)\
     .filter(extract('month', models.DailyLedger.entry_date) == month)\
     .filter(extract('year', models.DailyLedger.entry_date) == year)\
     .group_by(models.BOQItem.item_code).all()
     
    return results
