# إدارة قاعدة البيانات - دليل الاستخدام

## 🎯 التهيئة الأولى (مرة واحدة فقط)

عند بدء المشروع لأول مرة، قم بتشغيل:

```bash
python init_db.py
```

هذا سينشئ ملف `construction_system.db` مع جميع الجداول.

**⚠️ مهم جداً:** بعد التشغيل الأول، **احذف** أو اعمل comment للملف `init_db.py` أو على الأقل لا تشغله مرة أخرى!

---

## 🔄 استخدام Alembic للـ Migrations (موصى به للإنتاج)

### 1. تثبيت Alembic

```bash
pip install alembic
```

### 2. تهيئة Alembic

```bash
alembic init alembic
```

### 3. تعديل ملف `alembic.ini`

ابحث عن السطر:
```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```

واستبدله بـ:
```ini
sqlalchemy.url = sqlite:///construction_system.db
```

### 4. تعديل ملف `alembic/env.py`

أضف في بداية الملف:
```python
from database import Base
import models  # استيراد جميع الـ models
target_metadata = Base.metadata
```

### 5. إنشاء Migration جديد

كل ما تعدل في الـ models، قم بإنشاء migration:

```bash
alembic revision --autogenerate -m "وصف التعديل"
```

### 6. تطبيق الـ Migration

```bash
alembic upgrade head
```

### 7. التراجع عن Migration (لو لزم)

```bash
alembic downgrade -1
```

---

## 📝 مثال: إضافة عمود جديد

### الخطوات:

1. عدل الـ model في `models.py`:
```python
class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    budget = Column(Float, default=0.0)  # ← عمود جديد
```

2. أنشئ migration:
```bash
alembic revision --autogenerate -m "add budget to projects"
```

3. طبق التغيير:
```bash
alembic upgrade head
```

**✅ البيانات القديمة آمنة ولن تُحذف!**

---

## ⚠️ تحذيرات مهمة

1. **لا تستخدم** `Base.metadata.create_all()` في كود التطبيق الرئيسي
2. **لا تشغل** `init_db.py` أكثر من مرة
3. **استخدم** Alembic migrations لأي تعديلات مستقبلية
4. **اعمل Backup** لقاعدة البيانات قبل تطبيق أي migration

---

## 🔍 فحص الـ Migrations الحالية

```bash
alembic current
alembic history
```

---

## 🆘 استعادة من Backup

إذا حدث خطأ:
1. احذف ملف `construction_system.db`
2. استعد النسخة الاحتياطية
3. أو أعد تشغيل `init_db.py` وأدخل البيانات من جديد
