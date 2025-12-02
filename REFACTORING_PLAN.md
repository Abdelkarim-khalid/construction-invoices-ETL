# Backend Refactoring - Clean Architecture Implementation

## Goal Description

هنعيد هيكلة الـ backend الخاص بالـ Construction ERP عشان يكون منظم أكثر ويسهل الصيانة والتطوير على المدى الطويل. المشكلة الحالية إن كل الكود موجود في ملفات قليلة (`main.py`, `models.py`, `services/invoice_processor.py`) مما يصعب:

1. فهم flow الـ business logic
2. إضافة features جديدة بدون تعديلات كتيرة
3. اختبار الكود بشكل منفصل
4. الـ reusability للدوال والخدمات

**الحل:** تطبيق مبادئ الـ Clean Architecture مع Separation of Concerns:
- **Thin API Layer**: الـ endpoints تستقبل requests وتنادي الـ services
- **Thick Services Layer**: كل الـ business logic جوه الـ services
- **Utilities Layer**: helper functions مستقلة قابلة لإعادة الاستخدام
- **Clear Models Organization**: فصل الـ enums والـ models بشكل منطقي

الهدف **مش** إعادة كتابة الكود من الصفر، لكن **تنظيمه** في هيكل أفضل وقابل للتوسع.

---

## User Review Required

> [!IMPORTANT]
> **Migration Strategy**: هنعمل الـ refactoring بالتدريج عشان نضمن استمرارية الشغل:
> 1. إنشاء الهيكل الجديد (skeleton) جنباً إلى جنب مع الكود القديم
> 2. نقل الكود تدريجياً ملف ملف
> 3. اختبار كل جزء بعد نقله
> 4. حذف الملفات القديمة فقط بعد التأكد من استقرار الجديد
>
> **لن يتم حذف أي كود موجود حالياً** في هذه المرحلة، فقط إنشاء البنية الجديدة.

> [!NOTE]
> **Backward Compatibility**: الـ API endpoints هتفضل شغالة بنفس الطريقة، الفرونت إند (Streamlit) مش هيحتاج أي تعديلات غير بسيطة جداً.

---

## Proposed Changes

### Component 1: Core Infrastructure

هنبتدي بإنشاء الـ core modules اللي هتشيل الإعدادات والـ database setup.

#### [NEW] [config.py](file:///f:/EPR%20Invoice/construction_backend/app/core/config.py)
- Settings class باستخدام `pydantic-settings` (optional) أو dictionary بسيط
- البيانات زي: `DATABASE_URL`, `API_PREFIX`, `PROJECT_NAME`
- يمكن قراءتها من environment variables لاحقاً

#### [NEW] [session.py](file:///f:/EPR%20Invoice/construction_backend/app/db/session.py)
- نقل `engine`, `SessionLocal`, `get_db` من [database.py](file:///f:/EPR%20Invoice/construction_backend/database.py)
- إضافة أي initialization logic مستقبلية للـ database

#### [NEW] [base.py](file:///f:/EPR%20Invoice/construction_backend/app/db/base.py)
- نقل `Base = declarative_base()` من [database.py](file:///f:/EPR%20Invoice/construction_backend/database.py)
- استيراد كل الـ models عشان Alembic يشوفهم

---

### Component 2: Models Organization

هنقسّم الـ models الموجودة حالياً في ملف واحد ([models.py](file:///f:/EPR%20Invoice/construction_backend/models.py)) إلى ملفات منفصلة حسب الوظيفة.

#### [NEW] [enums.py](file:///f:/EPR%20Invoice/construction_backend/app/models/enums.py)
- نقل `InvoiceStatus`, `TradeType`, `RowType` من [models.py](file:///f:/EPR%20Invoice/construction_backend/models.py)
- إضافة أي enums جديدة مستقبلاً

#### [NEW] [project.py](file:///f:/EPR%20Invoice/construction_backend/app/models/project.py)
- نقل `Project` model من [models.py](file:///f:/EPR%20Invoice/construction_backend/models.py)

#### [NEW] [boq.py](file:///f:/EPR%20Invoice/construction_backend/app/models/boq.py)
- نقل `BOQItem` model من [models.py](file:///f:/EPR%20Invoice/construction_backend/models.py)

#### [NEW] [invoice.py](file:///f:/EPR%20Invoice/construction_backend/app/models/invoice.py)
- نقل `InvoiceLog`, `InvoiceDetail` models من [models.py](file:///f:/EPR%20Invoice/construction_backend/models.py)

#### [NEW] [staging.py](file:///f:/EPR%20Invoice/construction_backend/app/models/staging.py)
- نقل `StagingInvoiceDetail` model من [models.py](file:///f:/EPR%20Invoice/construction_backend/models.py)

#### [NEW] [ledger.py](file:///f:/EPR%20Invoice/construction_backend/app/models/ledger.py)
- نقل `DailyLedger` model من [models.py](file:///f:/EPR%20Invoice/construction_backend/models.py)

#### [NEW] [__init__.py](file:///f:/EPR%20Invoice/construction_backend/app/models/__init__.py)
- استيراد كل الـ models والـ enums عشان يبقى سهل الوصول ليهم

---

### Component 3: Pydantic Schemas

هنوسّع الـ schemas الموجودة وننظمها في ملفات منفصلة.

#### [MODIFY] [schemas/common.py](file:///f:/EPR%20Invoice/construction_backend/app/schemas/common.py)
- نقل `InvoiceStatusEnum` من [schemas.py](file:///f:/EPR%20Invoice/construction_backend/schemas.py)
- إضافة common schemas زي `Message`, `Status`, etc.

#### [NEW] [schemas/project.py](file:///f:/EPR%20Invoice/construction_backend/app/schemas/project.py)
- نقل `ProjectCreate`, `ProjectRead` من [schemas.py](file:///f:/EPR%20Invoice/construction_backend/schemas.py)

#### [NEW] [schemas/boq.py](file:///f:/EPR%20Invoice/construction_backend/app/schemas/boq.py)
- نقل `BOQItemBase`, `BOQItemCreate`, `BOQItemRead` من [schemas.py](file:///f:/EPR%20Invoice/construction_backend/schemas.py)

#### [NEW] [schemas/invoice.py](file:///f:/EPR%20Invoice/construction_backend/app/schemas/invoice.py)
- نقل `InvoiceLogBase`, `InvoiceLogCreate`, `InvoiceLogRead` من [schemas.py](file:///f:/EPR%20Invoice/construction_backend/schemas.py)
- نقل `InvoiceDetailBase`, `InvoiceDetailRead` من [schemas.py](file:///f:/EPR%20Invoice/construction_backend/schemas.py)

#### [NEW] [schemas/staging.py](file:///f:/EPR%20Invoice/construction_backend/app/schemas/staging.py)
- إنشاء schemas جديدة لـ Staging operations:
  - `StagingRowRead`: لعرض صف staging
  - `StagingRowUpdate`: لتعديل صف staging (is_valid, include_in_invoice, etc.)

---

### Component 4: Utilities

هنستخرج الـ helper functions من [invoice_processor.py](file:///f:/EPR%20Invoice/construction_backend/services/invoice_processor.py) ونخليها في utilities مستقلة.

#### [NEW] [parsing.py](file:///f:/EPR%20Invoice/construction_backend/app/utils/parsing.py)
- نقل `_parse_float` من [invoice_processor.py](file:///f:/EPR%20Invoice/construction_backend/services/invoice_processor.py)
- نقل `_normalize_trade` من [invoice_processor.py](file:///f:/EPR%20Invoice/construction_backend/services/invoice_processor.py)
- نقل `extract_phase_from_text` من [invoice_processor.py](file:///f:/EPR%20Invoice/construction_backend/services/invoice_processor.py)
- إضافة `classify_row`: دالة لتصنيف نوع الصف (ITEM, HEADER, TOTAL, etc.) - **new logic**

#### [NEW] [excel_reader.py](file:///f:/EPR%20Invoice/construction_backend/app/utils/excel_reader.py)
- دوال مساعدة لقراءة Excel وتحديد الأعمدة
- `detect_columns`: تحديد mapping الأعمدة من الـ DataFrame
- `read_excel_to_dataframe`: wrapper حول `pd.read_excel` مع error handling

---

### Component 5: Services (Business Logic)

هنفصل الـ business logic من [invoice_processor.py](file:///f:/EPR%20Invoice/construction_backend/services/invoice_processor.py) إلى services متخصصة.

#### [NEW] [projects_service.py](file:///f:/EPR%20Invoice/construction_backend/app/services/projects_service.py)
- `create_project`: إنشاء مشروع جديد
- `get_projects`: الحصول على قائمة المشاريع
- `get_project_by_id`: الحصول على مشروع بالـ ID

#### [NEW] [boq_service.py](file:///f:/EPR%20Invoice/construction_backend/app/services/boq_service.py)
- `add_boq_item`: إضافة بند BOQ جديد
- `get_boq_items`: الحصول على بنود BOQ لمشروع
- `match_boq_item`: البحث عن بند BOQ بالكود (helper for invoice processing)

#### [NEW] [invoice_import_service.py](file:///f:/EPR%20Invoice/construction_backend/app/services/invoice_import_service.py)
- استخراج الـ logic من `process_excel_invoice` في [invoice_processor.py](file:///f:/EPR%20Invoice/construction_backend/services/invoice_processor.py)
- `import_invoice_excel`: قراءة Excel → Staging
- `get_or_create_invoice`: الحصول على المستخلص أو إنشاءه
- استخدام utils من `excel_reader` و `parsing`

#### [NEW] [invoice_approval_service.py](file:///f:/EPR%20Invoice/construction_backend/app/services/invoice_approval_service.py)
- استخراج الـ logic من `approve_invoice` في [invoice_processor.py](file:///f:/EPR%20Invoice/construction_backend/services/invoice_processor.py)
- `build_invoice_details_from_staging`: نقل من Staging → InvoiceDetail
- `distribute_to_ledger`: توزيع الكميات على DailyLedger
- `validate_staging_rows`: التحقق من صحة صفوف Staging

#### [NEW] [staging_service.py](file:///f:/EPR%20Invoice/construction_backend/app/services/staging_service.py)
- `get_staging_rows`: الحصول على صفوف staging لمستخلص
- `update_staging_row`: تعديل صف staging (تصحيح errors، استبعاد صفوف)
- `update_staging_rows_bulk`: تعديل عدة صفوف دفعة واحدة

---

### Component 6: API Endpoints

هنقسّم الـ endpoints من [main.py](file:///f:/EPR%20Invoice/construction_backend/main.py) إلى routers منفصلة.

#### [NEW] [projects.py](file:///f:/EPR%20Invoice/construction_backend/app/api/v1/endpoints/projects.py)
- `GET /projects/`: list all projects
- `POST /projects/`: create new project
- `POST /boq/{project_id}`: add BOQ item (يمكن نقلها لـ router منفصل لاحقاً)

#### [NEW] [invoices.py](file:///f:/EPR%20Invoice/construction_backend/app/api/v1/endpoints/invoices.py)
- `POST /invoices/{invoice_id}/upload`: upload Excel invoice
- `GET /invoices/{invoice_id}/staging`: get staging data
- `PUT /invoices/{invoice_id}/staging`: update staging rows
- `POST /invoices/{invoice_id}/approve`: approve invoice

#### [NEW] [reports.py](file:///f:/EPR%20Invoice/construction_backend/app/api/v1/endpoints/reports.py)
- `GET /reports/schedule/{project_id}`: schedule report

#### [NEW] [__init__.py](file:///f:/EPR%20Invoice/construction_backend/app/api/v1/__init__.py)
- استيراد كل الـ routers

---

### Component 7: Main Application

#### [MODIFY] [main.py](file:///f:/EPR%20Invoice/construction_backend/app/main.py)
- تبسيط الملف ليكون فقط:
  - FastAPI app initialization
  - CORS middleware
  - Router inclusion من `api.v1`
  - Home endpoint
- إزالة كل الـ endpoint definitions

#### [NEW] [__init__.py](file:///f:/EPR%20Invoice/construction_backend/app/__init__.py)
- Empty file to make `app` a package

---

## Verification Plan

### Phase 1: Structure Verification
**When**: After creating all skeleton files
**How**: 
1. Run `python -m app.main` من مجلد `construction_backend`
2. تأكد إن الـ FastAPI app يبدأ بدون errors
3. افتح `http://localhost:8000/docs` وشوف الـ API documentation

### Phase 2: Import Testing
**When**: After migrating models and utils
**How**:
```bash
python -c "from app.models import Project, BOQItem, InvoiceLog; print('Models OK')"
python -c "from app.utils.parsing import parse_float, normalize_trade; print('Utils OK')"
```

### Phase 3: API Functionality Testing
**When**: After migrating services and endpoints
**How**:
1. استخدام existing [frontend.py](file:///f:/EPR%20Invoice/construction_backend/frontend.py) للتجربة
2. اختبار الـ flow الكامل:
   - إنشاء مشروع جديد
   - إضافة BOQ items
   - رفع Excel invoice
   - مراجعة staging data
   - اعتماد المستخلص
3. التأكد من النتائج في الـ database

### Phase 4: Database Compatibility
**When**: Throughout migration
**How**:
- الـ database schema مش هيتغير، بس الـ imports
- نستخدم نفس `construction_system.db` الموجود
- نتأكد إن Alembic migrations لسه شغالة

### Manual Testing Checklist
- [ ] FastAPI app starts without errors
- [ ] `/docs` endpoint accessible ويعرض كل الـ endpoints
- [ ] Create project via API
- [ ] Add BOQ item via API
- [ ] Upload Excel invoice (استخدام sample file)
- [ ] View staging data
- [ ] Approve invoice
- [ ] Generate schedule report
- [ ] Compare results with old implementation

---

## Migration Notes

**الخطوات المقترحة للتنفيذ:**

1. **Create skeleton** (هذه المرحلة):
   - إنشاء كل الملفات الجديدة مع basic structure
   - لا يتم حذف أي ملف قديم

2. **Migrate utilities** (المرحلة التالية):
   - نقل helper functions لـ `utils/`
   - اختبارها بشكل منفصل

3. **Migrate models** (بعدها):
   - نقل models لملفات منفصلة
   - تحديث الـ imports

4. **Migrate services** (بعدها):
   - نقل business logic لـ `services/`
   - اختبار كل service على حدى

5. **Migrate API endpoints** (الأخيرة):
   - نقل endpoints لـ routers
   - تحديث `main.py`
   - اختبار الـ integration الكامل

6. **Cleanup** (النهائية):
   - حذف الملفات القديمة بعد التأكد
   - تنظيف الـ imports
   - تحديث الـ documentation
