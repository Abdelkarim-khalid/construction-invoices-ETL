"""Wizard View for Invoice Upload"""

import streamlit as st
import pandas as pd
import io
from datetime import date
from frontend.api import client, invoices_api
from frontend.utils.helpers import get_col_letter

def render_wizard_view():
    st.header("📤 رفع ومعالجة المستخلصات")
    
    # Initialize session state for wizard if not exists
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

    progress = (st.session_state.step / 3) * 100
    st.progress(int(progress))

    # --- الخطوة 1 ---
    if st.session_state.step == 1:
        _render_step_1()

    # --- الخطوة 2 ---
    elif st.session_state.step == 2:
        _render_step_2()


def _render_step_1():
    st.subheader("الخطوة 1: الرفع واختيار الشيتات")

    proj_map = client.fetch_projects_list()
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


def _render_step_2():
    st.subheader("الخطوة 2: مطابقة الأعمدة")

    header_row = st.number_input(
        "📍 رقم صف العناوين في الإكسيل:", min_value=1, value=10
    )
    st.session_state.header_index = header_row - 1

    st.markdown("---")
    file = st.session_state.uploaded_file

    civil_df = None
    if st.session_state.sheet_civil:
        civil_map_ui, civil_df = _draw_mapper(
            file, st.session_state.sheet_civil, "civ"
        )
        st.session_state.mapping_civil = civil_map_ui
        st.markdown("---")

    elec_df = None
    if st.session_state.sheet_elec:
        elec_map_ui, elec_df = _draw_mapper(
            file, st.session_state.sheet_elec, "elec"
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
            _process_and_save(civil_df, elec_df)


def _draw_mapper(file, sheet_name, key_prefix):
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


def _process_and_save(civil_df, elec_df):
    proj_map = client.fetch_projects_list()
    if not proj_map:
        st.error("فشل الاتصال بالمشروع.")
        st.stop()

    project_id = proj_map[st.session_state.selected_proj_name]

    errors_log = []
    success_log = []

    if st.session_state.sheet_civil:
        is_ok, msg = _send_sheet(
            civil_df, st.session_state.mapping_civil, "civil", project_id
        )
        if is_ok:
            success_log.append(f"المدني: {msg}")
        else:
            errors_log.append(f"❌ خطأ مدني: {msg}")

    if st.session_state.sheet_elec:
        is_ok, msg = _send_sheet(
            elec_df, st.session_state.mapping_elec, "elec", project_id
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
        st.info("✅ العملية تمت بنجاح كامل. انتقل لصفحة الاعتماد للمراجعة.")


def _send_sheet(dataframe, mapping, trade_arg, project_id):
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
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
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
        "trade_type": trade_arg,
    }

    try:
        res = invoices_api.upload_invoice(files, data)
        if res.status_code == 200:
            return True, res.json().get("message", "تم الرفع بنجاح")
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
