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
API_URL = "http://127.0.0.1:8000/api/v1"


# --- Helper Functions ---
def get_col_letter(n):
    string_n = ""
    while n >= 0:
        n, remainder = divmod(n, 26)
        string_n = chr(65 + remainder) + string_n
        n -= 1
    return string_n


@st.cache_data(ttl=60)
def fetch_projects_list():
    try:
        res = requests.get(f"{API_URL}/projects/")
        if res.status_code == 200:
            return {f"{p['name']} (ID: {p['id']})": p["id"] for p in res.json()}
        return {}
    except:
        return {}


def reset_wizard():
    st.session_state.step = 1
    st.session_state.uploaded_file = None
    st.session_state.sheet_civil = None
    st.session_state.sheet_elec = None


# --- Session State Defaults ---
if "step" not in st.session_state:
    st.session_state.step = 1
if "mapping_civil" not in st.session_state:
    st.session_state.mapping_civil = {}
if "mapping_elec" not in st.session_state:
    st.session_state.mapping_elec = {}
if "header_index" not in st.session_state:
    st.session_state.header_index = 0
if "wiz_invoice_no" not in st.session_state:
    st.session_state.wiz_invoice_no = 1
if "staging_rows" not in st.session_state:
    st.session_state.staging_rows = []

# ==========================================
# 2. القائمة الجانبية (Sidebar)
# ==========================================
st.sidebar.title("القائمة الرئيسية")
menu = st.sidebar.radio(
    "تنقل بين الصفحات:",
    ["1. تأسيس مشروع", "2. معالج رفع المستخلصات (Wizard)", "3. الاعتماد والتقارير"],
    on_change=reset_wizard,
)

# ==========================================
# الصفحة 1: تأسيس مشروع
# ==========================================
if menu == "1. تأسيس مشروع":
    st.header("🛠️ تأسيس المشاريع")
    tab1, tab2 = st.tabs(["مشروع جديد", "إضافة بنود"])

    # ----- تبويب مشروع جديد -----
    with tab1:
        with st.form("new_proj"):
            name = st.text_input("اسم المشروع")
            loc = st.text_input("الموقع")
            if st.form_submit_button("حفظ") and name:
                try:
                    res = requests.post(
                        f"{API_URL}/projects/",
                        json={"name": name, "location": loc},
                    )
                    if res.status_code == 200:
                        st.success("تم الحفظ!")
                        fetch_projects_list.clear()
                    else:
                        st.error(f"خطأ: {res.text}")
                except Exception as e:
                    st.error(f"استثناء: {str(e)}")

    # ----- تبويب إضافة بنود -----
    with tab2:
        proj_map = fetch_projects_list()
        if proj_map:
            sel_proj = st.selectbox("اختر المشروع", proj_map.keys())
            pid = proj_map[sel_proj]
            with st.form("new_item"):
                c1, c2 = st.columns(2)
                code = c1.text_input("كود البند (مثال: 9-2)")
                unit = c1.text_input("الوحدة")
                price = c1.number_input("الفئة", min_value=0.0)
                desc = c2.text_area("الوصف")
                partial = c2.checkbox("مجزأ؟")
                if st.form_submit_button("إضافة"):
                    try:
                        res = requests.post(
                            f"{API_URL}/projects/{pid}/boq",
                            json={
                                "item_code": code,
                                "description": desc,
                                "unit": unit,
                                "unit_price": price,
                                "is_partial": partial,
                            },
                        )
                        if res.status_code == 200:
                            st.success(f"تم إضافة {code}")
                        else:
                            st.error(f"فشل الإضافة: {res.text}")
                    except Exception as e:
                        st.error(f"خطأ اتصال: {e}")
        else:
            st.warning("يرجى إنشاء مشروع أولاً.")

# ==========================================
# الصفحة 2: معالج رفع المستخلصات (Wizard)
# ==========================================
elif menu == "2. معالج رفع المستخلصات (Wizard)":
    st.header("📤 رفع ومعالجة المستخلصات")
    progress = (st.session_state.step / 3) * 100
    st.progress(int(progress))

    # --- الخطوة 1 ---
    if st.session_state.step == 1:
        st.subheader("الخطوة 1: الرفع واختيار الشيتات")

        proj_map = fetch_projects_list()
        if not proj_map:
            st.warning("لا توجد مشاريع.")
            st.stop()

        st.session_state.selected_proj_name = st.selectbox(
            "المشروع",
            proj_map.keys(),
            index=0
            if "selected_proj_name" not in st.session_state
            else list(proj_map.keys()).index(st.session_state.selected_proj_name),
        )

        c_inv, c_d1, c_d2 = st.columns([1, 1, 1])
        st.session_state.wiz_invoice_no = c_inv.number_input(
            "رقم المستخلص", min_value=1, value=st.session_state.wiz_invoice_no
        )
        st.session_state.start_date = c_d1.date_input(
            "من تاريخ", value=date.today()
        )
        st.session_state.end_date = c_d2.date_input(
            "إلى تاريخ", value=date.today()
        )

        uploaded = st.file_uploader("ملف المستخلص (Excel)", type=["xlsx", "xls"])

        if uploaded:
            st.session_state.uploaded_file = uploaded
            try:
                xl = pd.ExcelFile(uploaded)
                sheets = xl.sheet_names
                st.markdown("---")
                col_civ, col_elec = st.columns(2)
                with col_civ:
                    st.markdown("### 🏗️ الأعمال المدنية")
                    sheet_civ = st.selectbox("شيت المدني", ["-- لا يوجد --"] + sheets)
                    st.session_state.sheet_civil = (
                        sheet_civ if sheet_civ != "-- لا يوجد --" else None
                    )
                with col_elec:
                    st.markdown("### ⚡ أعمال الكهرباء")
                    sheet_elec = st.selectbox(
                        "شيت الكهرباء", ["-- لا يوجد --"] + sheets
                    )
                    st.session_state.sheet_elec = (
                        sheet_elec if sheet_elec != "-- لا يوجد --" else None
                    )
            except Exception as e:
                st.error(f"خطأ في الملف: {e}")

        st.markdown("---")
        col_back, col_space, col_next = st.columns([1, 6, 1])
        with col_back:
            st.button("⬅️ السابق", disabled=True)
        with col_next:
            if st.button("التالي ➡️", use_container_width=True):
                if not st.session_state.get("uploaded_file"):
                    st.error("يجب رفع ملف!")
                elif (
                    not st.session_state.sheet_civil
                    and not st.session_state.sheet_elec
                ):
                    st.error("اختر شيت واحد على الأقل!")
                else:
                    st.session_state.step = 2
                    st.rerun()

    # --- الخطوة 2 ---
    elif st.session_state.step == 2:
        st.subheader("الخطوة 2: مطابقة الأعمدة")

        header_row = st.number_input(
            "📍 رقم صف العناوين في الإكسيل:", min_value=1, value=10
        )
        st.session_state.header_index = header_row - 1

        st.markdown("---")
        file = st.session_state.uploaded_file

        def draw_mapper(sheet_name, key_prefix):
            st.markdown(f"### 📑 شيت: {sheet_name}")
            try:
                df = pd.read_excel(
                    file,
                    sheet_name=sheet_name,
                    header=st.session_state.header_index,
                )

                # تحويل أسماء الأعمدة لنصوص لضمان عدم حدوث مشاكل
                df.columns = df.columns.astype(str)

                st.write("عينة من البيانات:")
                st.dataframe(df.head(3))
                cols_options = [
                    f"{get_col_letter(i)} - {str(col)}"
                    for i, col in enumerate(df.columns)
                ]
                c1, c2, c3, c4 = st.columns(4)
                mapping = {}
                mapping["item_code"] = c1.selectbox(
                    "رقم البند", cols_options, key=f"{key_prefix}_code"
                )
                mapping["description"] = c2.selectbox(
                    "وصف البند", cols_options, key=f"{key_prefix}_desc"
                )
                mapping["qty"] = c3.selectbox(
                    "الكمية الحالية", cols_options, key=f"{key_prefix}_qty"
                )
                mapping["percentage"] = c4.selectbox(
                    "نسبة الصرف", cols_options, key=f"{key_prefix}_pct"
                )
                return mapping, df
            except Exception as e:
                st.error(f"خطأ قراءة الشيت: {e}")
                return None, None

        civil_df = None
        if st.session_state.sheet_civil:
            civil_map_ui, civil_df = draw_mapper(
                st.session_state.sheet_civil, "civ"
            )
            st.session_state.mapping_civil = civil_map_ui
            st.markdown("---")

        elec_df = None
        if st.session_state.sheet_elec:
            elec_map_ui, elec_df = draw_mapper(
                st.session_state.sheet_elec, "elec"
            )
            st.session_state.mapping_elec = elec_map_ui

        st.markdown("---")
        col_back, col_space, col_next = st.columns([1, 6, 2])
        with col_back:
            if st.button("⬅️ السابق", use_container_width=True):
                st.session_state.step = 1
                st.rerun()

        with col_next:
            if st.button("معالجة وحفظ ✅", use_container_width=True):
                proj_map = fetch_projects_list()
                if not proj_map:
                    st.error("فشل الاتصال بالمشروع.")
                    st.stop()

                project_id = proj_map[st.session_state.selected_proj_name]

                # --- دالة إرسال شيت معين للسيرفر ---
                def send_sheet(dataframe, mapping, trade_arg):
                    if dataframe is None:
                        return None, "No Data"

                    clean_map = {
                        k: v.split(" - ", 1)[1] for k, v in mapping.items()
                    }
                    rename_dict = {
                        clean_map["item_code"]: "item_code",
                        clean_map["description"]: "description",
                        clean_map["qty"]: "qty",
                        clean_map["percentage"]: "percentage",
                    }
                    df_ready = dataframe.rename(columns=rename_dict)

                    buffer = io.BytesIO()
                    try:
                        with pd.ExcelWriter(
                            buffer, engine="xlsxwriter"
                        ) as writer:
                            df_ready.to_excel(writer, index=False)
                    except:
                        df_ready.to_excel(buffer, index=False)
                    buffer.seek(0)

                    files = {
                        "file": (
                            "processed.xlsx",
                            buffer,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    }

                    data = {
                        "project_id": project_id,
                        "invoice_number": st.session_state.wiz_invoice_no,
                        "start_date": st.session_state.start_date,
                        "end_date": st.session_state.end_date,
                        "sheet_name": 0,
                        "trade_type": trade_arg,  # civil / elec
                    }

                    try:
                        res = requests.post(
                            f"{API_URL}/invoices/upload",
                            files=files,
                            data=data,
                        )
                        if res.status_code == 200:
                            return True, res.json().get(
                                "message", "تم الرفع بنجاح"
                            )
                        else:
                            try:
                                err_details = res.json()
                                if "detail" in err_details:
                                    return False, f"Server Error: {err_details['detail']}"
                                return False, f"Unknown Error: {err_details}"
                            except:
                                return False, f"Raw Error ({res.status_code}): {res.text}"
                    except Exception as e:
                        return False, f"Connection Error: {str(e)}"

                errors_log = []
                success_log = []

                if st.session_state.sheet_civil:
                    is_ok, msg = send_sheet(
                        civil_df, st.session_state.mapping_civil, "civil"
                    )
                    if is_ok:
                        success_log.append(f"المدني: {msg}")
                    else:
                        errors_log.append(f"❌ خطأ مدني: {msg}")

                if st.session_state.sheet_elec:
                    is_ok, msg = send_sheet(
                        elec_df, st.session_state.mapping_elec, "elec"
                    )
                    if is_ok:
                        success_log.append(f"الكهرباء: {msg}")
                    else:
                        errors_log.append(f"❌ خطأ كهرباء: {msg}")

                if errors_log:
                    for err in errors_log:
                        st.error(err)

                if success_log:
                    for s in success_log:
                        st.success(s)

                if not errors_log:
                    st.session_state.step = 1
                    st.info(
                        "✅ العملية تمت بنجاح كامل. انتقل لصفحة الاعتماد للمراجعة."
                    )

# ==========================================
# الصفحة 3: الاعتماد والتقارير
# ==========================================
elif menu == "3. الاعتماد والتقارير":
    st.header("📊 الاعتماد والتقارير")
    tab_rev, tab_rep = st.tabs(["مراجعة واعتماد", "التقارير"])

    # ---------- تبويب مراجعة واعتماد ----------
    with tab_rev:
        st.subheader("مراجعة بيانات المستخلص من الـ Staging")

        # رقم المستخلص
        col_in, col_btn = st.columns([1, 2])
        iid = col_in.number_input(
            "رقم المستخلص للمراجعة", value=1, min_value=1
        )

        # زرار جلب البيانات
        if col_btn.button("جلب البيانات للمراجعة"):
            try:
                res = requests.get(f"{API_URL}/invoices/{iid}/staging")
                if res.status_code == 200:
                    data = res.json()
                    if data:
                        st.session_state["staging_rows"] = data
                        st.success(
                            f"تم جلب {len(data)} صف من الـ Staging ✅"
                        )
                    else:
                        st.session_state["staging_rows"] = []
                        st.warning("لا توجد بيانات لهذا المستخلص.")
                else:
                    st.error(f"خطأ في الجلب: {res.text}")
            except Exception as e:
                st.error(f"فشل الاتصال: {e}")

        rows = st.session_state.get("staging_rows", [])

        if rows:
            df = pd.DataFrame(rows)

            st.markdown("---")
            st.markdown("### البيانات الخام من المستخلص (Staging)")
            st.caption(
                "يمكنك تعديل القيم يدويًا، واستبعاد البنود من الدخول للمستخلص عن طريق العمود include_in_invoice."
            )

            # اختيار عرض/إخفاء الصفوف المستبعدة
            show_ignored = st.checkbox(
                "عرض الصفوف المستبعدة (include_in_invoice = False)",
                value=False,
            )

            display_df = df.copy()
            if (
                not show_ignored
                and "include_in_invoice" in display_df.columns
            ):
                display_df = display_df[
                    display_df["include_in_invoice"] == True
                ]

            # نضمن وجود الأعمدة الأساسية
            for col_name in ["include_in_invoice", "is_valid", "row_type"]:
                if col_name not in display_df.columns:
                    if col_name == "include_in_invoice":
                        display_df[col_name] = True
                    else:
                        display_df[col_name] = None

            edited_df = st.data_editor(
                display_df,
                num_rows="fixed",
                key="staging_editor",
                column_config={
                    "id": st.column_config.Column(
                        disabled=True, label="ID"
                    ),
                    "invoice_id": st.column_config.Column(
                        disabled=True, label="Invoice ID"
                    ),
                    "row_index": st.column_config.Column(
                        disabled=True, label="رقم الصف"
                    ),
                    "row_type": st.column_config.Column(
                        disabled=True, label="نوع الصف"
                    ),
                    "is_valid": st.column_config.Column(
                        disabled=True, label="صالح؟"
                    ),
                    "error_message": st.column_config.Column(
                        disabled=True, label="ملاحظات الخطأ"
                    ),
                },
            )

            st.write(f"🔢 عدد الصفوف المعروضة: {len(edited_df)}")

            col_save, col_approve = st.columns(2)

            # زرار حفظ التعديلات (Soft Delete + تعديل يدوي)
            with col_save:
                if st.button(
                    "💾 حفظ التعديلات في الـ Staging",
                    use_container_width=True,
                ):
                    try:
                        payload = edited_df.to_dict(orient="records")
                        res = requests.put(
                            f"{API_URL}/invoices/{iid}/staging",
                            json=payload,
                        )
                        if res.status_code == 200:
                            st.success(
                                "تم حفظ التعديلات في الـ Staging بنجاح ✅"
                            )
                        else:
                            st.error(f"خطأ في الحفظ: {res.text}")
                    except Exception as e:
                        st.error(f"فشل الاتصال عند الحفظ: {e}")

            # زرار الاعتماد النهائي
            with col_approve:
                if st.button(
                    "✅ اعتماد نهائي وبناء بنود المستخلص",
                    use_container_width=True,
                ):
                    try:
                        res = requests.post(
                            f"{API_URL}/invoices/{iid}/approve"
                        )
                        if res.status_code == 200:
                            st.success(
                                "تم اعتماد المستخلص وإنشاء البنود النهائية في InvoiceDetails ✅"
                            )
                        else:
                            try:
                                err = res.json().get("detail", res.text)
                            except:
                                err = res.text
                            st.error(f"خطأ في الاعتماد: {err}")
                    except Exception as e:
                        st.error(f"فشل الاتصال عند الاعتماد: {e}")
        else:
            st.info(
                "من فضلك أدخل رقم المستخلص واضغط (جلب البيانات للمراجعة)."
            )

    # ---------- تبويب التقارير ----------
    with tab_rep:
        proj_map = fetch_projects_list()
        if proj_map:
            sel_proj = st.selectbox("المشروع للتقرير", proj_map.keys())
            pid = proj_map[sel_proj]
            c1, c2 = st.columns(2)
            month = c1.selectbox("الشهر", range(1, 13))
            year = c2.number_input("السنة", value=2025)
            if st.button("عرض التقرير"):
                try:
                    res = requests.get(
                        f"{API_URL}/reports/schedule/{pid}",
                        params={"month": month, "year": year},
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data:
                            df = pd.DataFrame(data)
                            st.table(df)
                            if (
                                "item_code" in df.columns
                                and "total_qty" in df.columns
                            ):
                                st.bar_chart(
                                    df.set_index("item_code")["total_qty"]
                                )
                        else:
                            st.info("لا توجد بيانات لهذه الفترة.")
                    else:
                        st.error(res.text)
                except Exception as e:
                    st.error(f"فشل الاتصال: {e}")
        else:
            st.warning("لا توجد مشاريع لعرض التقارير.")
