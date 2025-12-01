import streamlit as st
import pandas as pd
import requests
from datetime import date
import io
import string

# ==========================================
# 1. إعدادات الصفحة والتهيئة
# ==========================================
st.set_page_config(page_title="Mini ERP - Construction", layout="wide")
API_URL = "http://127.0.0.1:8000"

# --- دوال مساعدة (Helpers) ---

def get_col_letter(n):
    """تحويل رقم العمود لحرف (0->A, 1->B...)"""
    string_n = ""
    while n >= 0:
        n, remainder = divmod(n, 26)
        string_n = chr(65 + remainder) + string_n
        n -= 1
    return string_n

def get_projects_map():
    """جلب قائمة المشاريع من السيرفر"""
    try:
        res = requests.get(f"{API_URL}/projects/")
        if res.status_code == 200:
            return {f"{p['name']} (ID: {p['id']})": p['id'] for p in res.json()}
        return {}
    except:
        return {}

def reset_wizard():
    """تصفير خطوات المعالج عند تغيير الصفحة"""
    st.session_state.step = 1
    st.session_state.uploaded_file = None
    st.session_state.sheet_civil = None
    st.session_state.sheet_elec = None

# --- تهيئة متغيرات الجلسة (Session State) ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'mapping_civil' not in st.session_state: st.session_state.mapping_civil = {}
if 'mapping_elec' not in st.session_state: st.session_state.mapping_elec = {}
if 'header_index' not in st.session_state: st.session_state.header_index = 0

# ==========================================
# 2. القائمة الجانبية (Sidebar)
# ==========================================
st.sidebar.title("القائمة الرئيسية")
menu = st.sidebar.radio(
    "تنقل بين الصفحات:",
    ["1. تأسيس مشروع", "2. معالج رفع المستخلصات (Wizard)", "3. الاعتماد والتقارير"],
    on_change=reset_wizard 
)

# ==========================================
# الصفحة 1: تأسيس مشروع
# ==========================================
if menu == "1. تأسيس مشروع":
    st.header("🛠️ تأسيس المشاريع")
    tab1, tab2 = st.tabs(["مشروع جديد", "إضافة بنود"])
    
    with tab1:
        with st.form("new_proj"):
            name = st.text_input("اسم المشروع")
            loc = st.text_input("الموقع")
            if st.form_submit_button("حفظ") and name:
                try:
                    res = requests.post(f"{API_URL}/projects/", json={"name": name, "location": loc})
                    if res.status_code == 200: st.success("تم الحفظ!")
                except Exception as e: st.error(str(e))

    with tab2:
        proj_map = get_projects_map()
        if proj_map:
            sel_proj = st.selectbox("اختر المشروع", proj_map.keys())
            pid = proj_map[sel_proj]
            with st.form("new_item"):
                c1, c2 = st.columns(2)
                code = c1.text_input("كود البند")
                unit = c1.text_input("الوحدة")
                price = c1.number_input("الفئة", min_value=0.0)
                desc = c2.text_area("الوصف")
                partial = c2.checkbox("مجزأ؟")
                if st.form_submit_button("إضافة"):
                    try:
                        requests.post(f"{API_URL}/boq/{pid}", json={
                            "item_code": code, "description": desc,
                            "unit": unit, "unit_price": price, "is_partial": partial
                        })
                        st.success(f"تم إضافة {code}")
                    except: st.error("فشل الاتصال")
        else:
            st.warning("يرجى إنشاء مشروع أولاً.")

# ==========================================
# الصفحة 2: معالج رفع المستخلصات (Wizard)
# ==========================================
elif menu == "2. معالج رفع المستخلصات (Wizard)":
    st.header("📤 رفع ومعالجة المستخلصات")
    
    # شريط التقدم
    progress = (st.session_state.step / 3) * 100
    st.progress(int(progress))

    # ---------------------------------------
    # الخطوة 1: الرفع واختيار الشيتات
    # ---------------------------------------
    if st.session_state.step == 1:
        st.subheader("الخطوة 1: رفع الملف وتحديد الشيتات")
        
        proj_map = get_projects_map()
        if not proj_map:
            st.warning("لا توجد مشاريع. أسس مشروعاً أولاً.")
            st.stop()
            
        st.session_state.selected_proj_name = st.selectbox(
            "المشروع", proj_map.keys(), 
            index=0 if 'selected_proj_name' not in st.session_state else list(proj_map.keys()).index(st.session_state.selected_proj_name)
        )
        
        c1, c2 = st.columns(2)
        st.session_state.start_date = c1.date_input("من تاريخ", value=date.today())
        st.session_state.end_date = c2.date_input("إلى تاريخ", value=date.today())

        uploaded = st.file_uploader("ملف المستخلص (Excel)", type=["xlsx", "xls"])
        
        if uploaded:
            st.session_state.uploaded_file = uploaded
            try:
                xl = pd.ExcelFile(uploaded)
                sheets = xl.sheet_names
                
                st.markdown("---")
                st.info("قم باختيار الشيت المناسب لكل تخصص (يمكن ترك أحدهما فارغاً)")
                
                col_civ, col_elec = st.columns(2)
                with col_civ:
                    st.markdown("### 🏗️ الأعمال المدنية")
                    sheet_civ = st.selectbox("شيت المدني", ["-- لا يوجد --"] + sheets)
                    st.session_state.sheet_civil = sheet_civ if sheet_civ != "-- لا يوجد --" else None

                with col_elec:
                    st.markdown("### ⚡ أعمال الكهرباء")
                    sheet_elec = st.selectbox("شيت الكهرباء", ["-- لا يوجد --"] + sheets)
                    st.session_state.sheet_elec = sheet_elec if sheet_elec != "-- لا يوجد --" else None

            except Exception as e:
                st.error(f"خطأ في الملف: {e}")

        # --- أزرار التنقل (تنسيق محسن) ---
        st.markdown("---")
        # التقسيم: [سابق] --فراغ-- [تالي]
        col_back, col_space, col_next = st.columns([1, 6, 1])
        
        with col_back:
            st.button("⬅️ السابق", disabled=True)
            
        with col_next:
            if st.button("التالي ➡️", use_container_width=True):
                if not st.session_state.get('uploaded_file'):
                    st.error("يجب رفع ملف أولاً!")
                elif not st.session_state.sheet_civil and not st.session_state.sheet_elec:
                    st.error("يجب اختيار شيت واحد على الأقل!")
                else:
                    st.session_state.step = 2
                    st.rerun()

    # ---------------------------------------
    # الخطوة 2: مطابقة الأعمدة (Mapping)
    # ---------------------------------------
    elif st.session_state.step == 2:
        st.subheader("الخطوة 2: مطابقة الأعمدة")
        
        # خانة تحديد رقم صف العناوين
        header_row = st.number_input(
            "📍 **رقم صف العناوين في الإكسيل:** (لتجاهل اللوجو والبيانات العلوية)", 
            min_value=1, 
            value=10, 
            help="اكتب رقم الصف الذي يحتوي على (رقم البند، الكمية..) في ملف الإكسيل."
        )
        st.session_state.header_index = header_row - 1
        
        st.markdown("---")
        file = st.session_state.uploaded_file
        
        # دالة الرسم (مع تمرير الـ header_index)
        def draw_mapper(sheet_name, key_prefix):
            st.markdown(f"### 📑 شيت: {sheet_name}")
            try:
                # قراءة مع تخطي الصفوف العلوية
                df = pd.read_excel(file, sheet_name=sheet_name, header=st.session_state.header_index)
                
                st.write("عينة من البيانات:")
                st.dataframe(df.head(3))
                
                cols_options = [f"{get_col_letter(i)} - {str(col)}" for i, col in enumerate(df.columns)]
                
                c1, c2, c3, c4 = st.columns(4)
                mapping = {}
                mapping['item_code'] = c1.selectbox(f"رقم البند", cols_options, key=f"{key_prefix}_code")
                mapping['description'] = c2.selectbox(f"وصف البند", cols_options, key=f"{key_prefix}_desc")
                mapping['qty'] = c3.selectbox(f"الكمية الحالية", cols_options, key=f"{key_prefix}_qty")
                mapping['percentage'] = c4.selectbox(f"نسبة الصرف", cols_options, key=f"{key_prefix}_pct")
                
                return mapping, df
            except Exception as e:
                st.error(f"خطأ في قراءة الشيت (تأكد من رقم صف العناوين): {e}")
                return None, None

        # رسم الواجهات
        civil_df = None
        if st.session_state.sheet_civil:
            civil_map_ui, civil_df = draw_mapper(st.session_state.sheet_civil, "civ")
            st.session_state.mapping_civil = civil_map_ui
            st.markdown("---")

        elec_df = None
        if st.session_state.sheet_elec:
            elec_map_ui, elec_df = draw_mapper(st.session_state.sheet_elec, "elec")
            st.session_state.mapping_elec = elec_map_ui

        # --- أزرار التنقل (تنسيق محسن) ---
        st.markdown("---")
        col_back, col_space, col_next = st.columns([1, 6, 2]) # مساحة للزر الكبير
        
        with col_back:
            if st.button("⬅️ السابق", use_container_width=True):
                st.session_state.step = 1
                st.rerun()
                
        with col_next:
            if st.button("معالجة البيانات وحفظها ✅", use_container_width=True):
                
                # 1. إصلاح الخطأ: استدعاء القائمة مرة أخرى هنا
                proj_map = get_projects_map()
                
                if not proj_map:
                    st.error("فشل في الاتصال بالسيرفر أو لا توجد مشاريع.")
                    st.stop()

                project_id = proj_map[st.session_state.selected_proj_name]
                
                # دالة الإرسال الداخلية
                def send_sheet(dataframe, mapping, type_suffix):
                    if dataframe is None: return None
                    
                    clean_map = {}
                    for k, v in mapping.items():
                        original_col_name = v.split(" - ", 1)[1]
                        clean_map[k] = original_col_name
                    
                    # إعادة التسمية لتوافق السيرفر
                    rename_dict = {
                        clean_map['item_code']: 'item_code',
                        clean_map['description']: 'description',
                        clean_map['qty']: 'qty',
                        clean_map['percentage']: 'percentage'
                    }
                    
                    df_ready = dataframe.rename(columns=rename_dict)
                    
                    # الحفظ في الذاكرة
                    buffer = io.BytesIO()
                    try:
                        # نحتاج مكتبة xlsxwriter
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_ready.to_excel(writer, index=False)
                    except:
                        # بديل لو xlsxwriter مش موجود
                        df_ready.to_excel(buffer, index=False)
                        
                    buffer.seek(0)
                    
                    files = {"file": ("processed.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                    data = {
                        "project_id": project_id,
                        "invoice_number": 1, 
                        "start_date": st.session_state.start_date,
                        "end_date": st.session_state.end_date,
                        "sheet_name": 0 
                    }
                    
                    return requests.post(f"{API_URL}/upload-invoice/", files=files, data=data)

                # التنفيذ
                success_msg = ""
                
                if st.session_state.sheet_civil:
                    res = send_sheet(civil_df, st.session_state.mapping_civil, "Civil")
                    if res and res.status_code == 200: success_msg += "✅ تم رفع المدني بنجاح.\n"
                    else: st.error(f"خطأ في المدني: {res.text if res else 'Error'}")

                if st.session_state.sheet_elec:
                    res = send_sheet(elec_df, st.session_state.mapping_elec, "Elec")
                    if res and res.status_code == 200: success_msg += "✅ تم رفع الكهرباء بنجاح.\n"
                    else: st.error(f"خطأ في الكهرباء: {res.text if res else 'Error'}")

                if success_msg:
                    st.success(success_msg)
                    st.session_state.step = 1 
                    st.info("انتقل لصفحة الاعتماد للمراجعة النهائية.")

# ==========================================
# الصفحة 3: الاعتماد والتقارير
# ==========================================
elif menu == "3. الاعتماد والتقارير":
    st.header("📊 الاعتماد والتقارير")
    
    tab_rev, tab_rep = st.tabs(["مراجعة واعتماد", "التقارير"])
    
    with tab_rev:
        st.info("هنا تظهر البيانات التي تم رفعها (Staging) قبل إدخالها الحسابات.")
        # تحسين مستقبلي: جعل رقم المستخلص قائمة منسدلة
        iid = st.number_input("رقم المستخلص للمراجعة", value=1)
        
        if st.button("جلب البيانات للمراجعة"):
            try:
                res = requests.get(f"{API_URL}/invoices/{iid}/staging")
                if res.status_code == 200:
                    data = res.json()
                    if data:
                        df = pd.DataFrame(data)
                        st.dataframe(df)
                    else:
                        st.warning("لا توجد بيانات (قد يكون المستخلص فارغاً أو تم اعتماده سابقاً).")
                else: st.error("خطأ في الاتصال")
            except: st.error("فشل الاتصال")
            
        st.markdown("---")
        if st.button("✅ اعتماد نهائي (Approve)", type="primary"):
            try:
                res = requests.post(f"{API_URL}/invoices/{iid}/approve")
                if res.status_code == 200:
                    st.balloons()
                    st.success("تم الاعتماد وتوليد القيود اليومية بنجاح!")
                else:
                    st.error(f"خطأ: {res.text}")
            except: st.error("فشل الاتصال")

    with tab_rep:
        st.subheader("تقرير البرنامج الزمني (توزيع الكميات)")
        proj_map = get_projects_map()
        if proj_map:
            sel_proj = st.selectbox("المشروع للتقرير", proj_map.keys())
            pid = proj_map[sel_proj]
            
            c1, c2 = st.columns(2)
            month = c1.selectbox("الشهر", range(1, 13))
            year = c2.number_input("السنة", value=2025)
            
            if st.button("عرض التقرير"):
                try:
                    res = requests.get(f"{API_URL}/reports/schedule/{pid}", params={"month": month, "year": year})
                    if res.status_code == 200:
                        data = res.json()
                        if data:
                            df = pd.DataFrame(data)
                            st.table(df)
                            st.bar_chart(df.set_index("item_code")['total_qty'])
                        else:
                            st.info("لا توجد كميات موزعة في هذا الشهر.")
                    else: st.error(res.text)
                except Exception as e: st.error(str(e))