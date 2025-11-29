from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from database import Base  # تأكد ان ملف database.py موجود وفيه تعريف Base
import enum

# =========================================================
# 1. Enums: حالات المستخلص للتحكم في دورة العمل
# =========================================================
class InvoiceStatus(enum.Enum):
    DRAFT = "draft"         # مرحلة الرفع والتصحيح (Staging)
    REVIEW = "review"       # مرحلة المراجعة (Clean Copy)
    APPROVED = "approved"   # مرحلة الاعتماد النهائي وتوليد الـ Ledger

# =========================================================
# 2. Projects: المشاريع
# =========================================================
class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)
    
    # العلاقات (Relationships)
    boq_items = relationship("BOQItem", back_populates="project")
    invoices = relationship("InvoiceLog", back_populates="project")
    ledger_entries = relationship("DailyLedger", back_populates="project")

# =========================================================
# 3. BOQ Items: بنود المقايسة (العقد)
# =========================================================
class BOQItem(Base):
    __tablename__ = 'boq_items'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    
    item_code = Column(String, index=True)  # مثال: "9-2"
    description = Column(String)            # الوصف الرئيسي: "توريد وتركيب باب خشب.."
    unit = Column(String)                   # الوحدة: م3، عدد، مقطوعية
    unit_price = Column(Float, default=0.0) # سعر الفئة في العقد
    
    # هام: هل البند مجزأ؟ (حلوق/ضلف) - لتنبيه الواجهة
    is_partial = Column(Boolean, default=False) 
    
    # العلاقات
    project = relationship("Project", back_populates="boq_items")
    invoice_details = relationship("InvoiceDetail", back_populates="boq_item")
    ledger_entries = relationship("DailyLedger", back_populates="boq_item")

# =========================================================
# 4. Invoice Log: سجل المستخلصات (Header)
# =========================================================
class InvoiceLog(Base):
    __tablename__ = 'invoices_log'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    
    invoice_number = Column(Integer, index=True)  # رقم المستخلص: 1، 2، 3
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    
    # تواريخ المستخلص (لحساب التوزيع الزمني)
    period_start = Column(Date)
    period_end = Column(Date)
    
    # Linked List Pattern: للتحديث التعاقبي
    # يشير للمستخلص السابق لحساب التراكمي أوتوماتيكياً
    previous_invoice_id = Column(Integer, ForeignKey('invoices_log.id'), nullable=True)
    
    # العلاقات
    project = relationship("Project", back_populates="invoices")
    details = relationship("InvoiceDetail", back_populates="invoice")
    staging_data = relationship("StagingInvoiceDetail", back_populates="invoice")
    ledger_entries = relationship("DailyLedger", back_populates="invoice")
    
    # علاقة ذاتية للوصول للمستخلص السابق
    previous_invoice = relationship("InvoiceLog", remote_side=[id])

# =========================================================
# 5. Staging Area: منطقة التجهيز (المسودة)
# تستقبل البيانات الخام من الإكسيل قبل التنظيف
# =========================================================
class StagingInvoiceDetail(Base):
    __tablename__ = 'staging_invoice_details'
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey('invoices_log.id'))
    
    row_index = Column(Integer)  # رقم السطر في الإكسيل
    
    # حقول نصية (String) لاستيعاب الأخطاء
    raw_item_code = Column(String, nullable=True) 
    raw_description = Column(String, nullable=True) # الوصف كامل بالأقواس
    raw_qty = Column(String, nullable=True)         # الكمية كنص
    raw_percentage = Column(String, nullable=True)  # النسبة كنص
    
    # نتيجة الفحص (Validation)
    is_valid = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    invoice = relationship("InvoiceLog", back_populates="staging_data")

# =========================================================
# 6. Invoice Details: تفاصيل المستخلص (الدفتر الفعلي)
# =========================================================
class InvoiceDetail(Base):
    __tablename__ = 'invoice_details'
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey('invoices_log.id'))
    boq_item_id = Column(Integer, ForeignKey('boq_items.id'))
    
    # الوصف المستخرج (ما بين الأقواس): "حلوق"، "ضلف"
    row_description = Column(String, nullable=True) 
    
    # -----------------------------------------------------
    # الكميات والنسب (Input & Reconciliation)
    # -----------------------------------------------------
    current_percentage = Column(Float, default=100.0) # نسبة الصرف (20%)
    
    claimed_qty = Column(Float, default=0.0)    # كمية المقاول (7 أبواب)
    approved_qty = Column(Float, default=0.0)   # الكمية المعتمدة (7 أبواب) - قابلة للتسوية
    
    # -----------------------------------------------------
    # الكمية المكافئة (Calculated Logic)
    # هامة جداً للبرنامج الزمني وفروق الأسعار
    # المعادلة: approved_qty * (current_percentage / 100)
    # النتيجة: 1.4 باب
    # -----------------------------------------------------
    equivalent_qty = Column(Float, default=0.0)
    
    # -----------------------------------------------------
    # الأرصدة التراكمية
    # -----------------------------------------------------
    previous_cumulative_qty = Column(Float, default=0.0) 
    total_cumulative_qty = Column(Float, default=0.0)    # = prev + equivalent_qty (عادة بنجمع المكافئ في التراكمي المالي)
    
    # القيم المالية
    unit_price_at_time = Column(Float) # السعر وقت التنفيذ
    total_value = Column(Float, default=0.0) # القيمة المالية للكمية الحالية
    
    notes = Column(Text) # ملاحظات التسوية
    
    # العلاقات
    invoice = relationship("InvoiceLog", back_populates="details")
    boq_item = relationship("BOQItem", back_populates="invoice_details")

# =========================================================
# 7. Daily Ledger: دفتر اليومية الموزع (للحصر الزمني)
# يتم تعبئته أوتوماتيكياً عند اعتماد المستخلص (تفتيت الكمية)
# =========================================================
class DailyLedger(Base):
    __tablename__ = 'daily_ledger'
    
    id = Column(Integer, primary_key=True, index=True)
    
    project_id = Column(Integer, ForeignKey('projects.id'))
    invoice_id = Column(Integer, ForeignKey('invoices_log.id'))
    boq_item_id = Column(Integer, ForeignKey('boq_items.id'))
    
    entry_date = Column(Date, index=True) # التاريخ (يوم بيوم)
    
    # الكمية الموزعة (Distributed Equivalent Quantity)
    # لو الـ equivalent_qty = 1.4 والمدة 14 يوم
    # هنا هينزل: 0.1
    distributed_qty = Column(Float, default=0.0) 
    
    # العلاقات
    project = relationship("Project", back_populates="ledger_entries")
    invoice = relationship("InvoiceLog", back_populates="ledger_entries")
    boq_item = relationship("BOQItem", back_populates="ledger_entries")