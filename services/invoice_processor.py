import pandas as pd
from sqlalchemy.orm import Session
from models import InvoiceLog, InvoiceDetail, BOQItem, DailyLedger, Project
from datetime import timedelta, date

def process_excel_invoice(db: Session, project_id: int, file_path: str, inv_number: str, start_date: date, end_date: date):
    # 1. تسجيل المستخلص في الـ Log
    new_invoice = InvoiceLog(
        project_id=project_id,
        invoice_number=inv_number,
        file_name=file_path.split("/")[-1], # اسم الملف فقط
        period_start=start_date,
        period_end=end_date
    )
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    # 2. قراءة ملف الإكسيل (تعديل الأعمدة حسب ملفك الحقيقي)
    # نفترض أن الإكسيل يحتوي أعمدة: Code, Description, Total_Qty, Percentage
    df = pd.read_excel(file_path)
    
    # تنظيف البيانات (حذف الصفوف الفارغة)
    df = df.dropna(subset=['Code']) 

    # 3. اللوب على كل سطر في الإكسيل
    for index, row in df.iterrows():
        item_code = str(row['Code'])
        description = str(row.get('Description', ''))
        current_total_qty = float(row.get('Total_Qty', 0))
        pct = float(row.get('Percentage', 1.0)) # لو مش موجودة نعتبرها 100%

        # البحث عن البند في المقايسة
        boq_item = db.query(BOQItem).filter_by(project_id=project_id, item_code=item_code).first()
        
        if not boq_item:
            print(f"Warning: Item {item_code} not found in BOQ. Skipping.")
            continue

        # --- خوارزمية حساب السابق (Previous Qty) ---
        # نبحث عن آخر مستخلص لهذا البند، ولهذا الوصف (النسبة)
        # الهدف: مقارنة "حلوق" بـ "حلوق" و "ضلف" بـ "ضلف"
        prev_detail = db.query(InvoiceDetail).join(InvoiceLog).filter(
            InvoiceLog.project_id == project_id,
            InvoiceLog.id < new_invoice.id, # مستخلصات أقدم
            InvoiceDetail.boq_item_id == boq_item.id,
            InvoiceDetail.completion_pct == pct # نفس النسبة بالضبط
        ).order_by(InvoiceLog.period_end.desc()).first()

        prev_qty = prev_detail.total_qty if prev_detail else 0.0
        
        # --- الحسابات المالية والكمية ---
        delta_qty = current_total_qty - prev_qty # الكمية المنفذة هذا الشهر (Current)
        
        gross_value = current_total_qty * boq_item.unit_price
        net_value = gross_value * pct

        # 4. تخزين التفاصيل (Snapshot)
        detail_entry = InvoiceDetail(
            invoice_id=new_invoice.id,
            boq_item_id=boq_item.id,
            row_description=description,
            completion_pct=pct,
            previous_qty=prev_qty,
            current_qty=delta_qty,   # دي الكمية اللي هتتوزع على الأيام
            total_qty=current_total_qty,
            total_value_gross=gross_value,
            total_value_net=net_value
        )
        db.add(detail_entry)

        # 5. التوزيع اليومي (Daily Ledger Logic)
        # فقط إذا كان هناك كمية تم تنفيذها (Delta != 0)
        if delta_qty != 0:
            total_days = (end_date - start_date).days + 1
            if total_days > 0:
                daily_rate = delta_qty / total_days
                
                # Loop لإنشاء سجل لكل يوم
                for i in range(total_days):
                    current_day = start_date + timedelta(days=i)
                    ledger_entry = DailyLedger(
                        entry_date=current_day,
                        boq_item_id=boq_item.id,
                        source_invoice_id=new_invoice.id,
                        daily_qty=daily_rate
                    )
                    db.add(ledger_entry)

    db.commit()
    return {"status": "success", "invoice_id": new_invoice.id}
