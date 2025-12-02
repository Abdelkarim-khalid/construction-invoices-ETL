"""Reports and Approval View"""

import streamlit as st
import pandas as pd
from frontend.api import client, invoices_api

def render_reports_view():
    st.header("📊 الاعتماد والتقارير")
    tab_rev, tab_rep = st.tabs(["مراجعة واعتماد", "التقارير"])

    # ---------- تبويب مراجعة واعتماد ----------
    with tab_rev:
        _render_approval_tab()

    # ---------- تبويب التقارير ----------
    with tab_rep:
        _render_reports_tab()


def _render_approval_tab():
    st.subheader("مراجعة بيانات المستخلص من الـ Staging")

    # رقم المستخلص
    col_in, col_btn = st.columns([1, 2])
    iid = col_in.number_input(
        "رقم المستخلص للمراجعة", value=1, min_value=1
    )

    # زرار جلب البيانات
    if col_btn.button("جلب البيانات للمراجعة"):
        try:
            res = invoices_api.get_staging_data(iid)
            if res.status_code == 200:
                data = res.json()
                if data:
                    st.session_state["staging_rows"] = data
                    st.success(f"تم جلب {len(data)} صف من الـ Staging ✅")
                else:
                    st.session_state["staging_rows"] = []
                    st.warning("لا توجد بيانات لهذا المستخلص.")
            else:
                st.error(f"خطأ في الجلب: {res.text}")
        except Exception as e:
            st.error(f"فشل الاتصال: {e}")

    rows = st.session_state.get("staging_rows", [])

    if rows:
        _render_staging_table(rows, iid)
    else:
        st.info("من فضلك أدخل رقم المستخلص واضغط (جلب البيانات للمراجعة).")


def _render_staging_table(rows, iid):
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
    if not show_ignored and "include_in_invoice" in display_df.columns:
        display_df = display_df[display_df["include_in_invoice"] == True]

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
            "id": st.column_config.Column(disabled=True, label="ID"),
            "invoice_id": st.column_config.Column(disabled=True, label="Invoice ID"),
            "row_index": st.column_config.Column(disabled=True, label="رقم الصف"),
            "row_type": st.column_config.Column(disabled=True, label="نوع الصف"),
            "is_valid": st.column_config.Column(disabled=True, label="صالح؟"),
            "error_message": st.column_config.Column(disabled=True, label="ملاحظات الخطأ"),
        },
    )

    st.write(f"🔢 عدد الصفوف المعروضة: {len(edited_df)}")

    col_save, col_approve = st.columns(2)

    # زرار حفظ التعديلات
    with col_save:
        if st.button("💾 حفظ التعديلات في الـ Staging", use_container_width=True):
            try:
                payload = edited_df.to_dict(orient="records")
                res = invoices_api.update_staging_data(iid, payload)
                if res.status_code == 200:
                    st.success("تم حفظ التعديلات في الـ Staging بنجاح ✅")
                else:
                    st.error(f"خطأ في الحفظ: {res.text}")
            except Exception as e:
                st.error(f"فشل الاتصال عند الحفظ: {e}")

    # زرار الاعتماد النهائي
    with col_approve:
        if st.button("✅ اعتماد نهائي وبناء بنود المستخلص", use_container_width=True):
            try:
                res = invoices_api.approve_invoice(iid)
                if res.status_code == 200:
                    st.success("تم اعتماد المستخلص وإنشاء البنود النهائية في InvoiceDetails ✅")
                else:
                    try:
                        err = res.json().get("detail", res.text)
                    except:
                        err = res.text
                    st.error(f"خطأ في الاعتماد: {err}")
            except Exception as e:
                st.error(f"فشل الاتصال عند الاعتماد: {e}")


def _render_reports_tab():
    proj_map = client.fetch_projects_list()
    if proj_map:
        sel_proj = st.selectbox("المشروع للتقرير", proj_map.keys())
        pid = proj_map[sel_proj]
        c1, c2 = st.columns(2)
        month = c1.selectbox("الشهر", range(1, 13))
        year = c2.number_input("السنة", value=2025)
        if st.button("عرض التقرير"):
            try:
                res = invoices_api.get_schedule_report(pid, month, year)
                if res.status_code == 200:
                    data = res.json()
                    if data:
                        df = pd.DataFrame(data)
                        st.table(df)
                        if "item_code" in df.columns and "total_qty" in df.columns:
                            st.bar_chart(df.set_index("item_code")["total_qty"])
                    else:
                        st.info("لا توجد بيانات لهذه الفترة.")
                else:
                    st.error(res.text)
            except Exception as e:
                st.error(f"فشل الاتصال: {e}")
    else:
        st.warning("لا توجد مشاريع لعرض التقارير.")
