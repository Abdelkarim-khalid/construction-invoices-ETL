"""Projects View"""

import streamlit as st
from frontend.api import client, projects_api

def render_projects_view():
    st.header("🛠️ تأسيس المشاريع")
    tab1, tab2 = st.tabs(["مشروع جديد", "إضافة بنود"])

    # ----- تبويب مشروع جديد -----
    with tab1:
        with st.form("new_proj"):
            name = st.text_input("اسم المشروع")
            loc = st.text_input("الموقع")
            if st.form_submit_button("حفظ") and name:
                try:
                    res = projects_api.create_project(name, loc)
                    if res.status_code == 200:
                        st.success("تم الحفظ!")
                        client.fetch_projects_list.clear() # Clear cache
                    else:
                        st.error(f"خطأ: {res.text}")
                except Exception as e:
                    st.error(f"استثناء: {str(e)}")

    # ----- تبويب إضافة بنود -----
    with tab2:
        proj_map = client.fetch_projects_list()
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
                        item_data = {
                            "item_code": code,
                            "description": desc,
                            "unit": unit,
                            "unit_price": price,
                            "is_partial": partial,
                        }
                        res = projects_api.add_boq_item(pid, item_data)
                        if res.status_code == 200:
                            st.success(f"تم إضافة {code}")
                        else:
                            st.error(f"فشل الإضافة: {res.text}")
                    except Exception as e:
                        st.error(f"خطأ اتصال: {e}")
        else:
            st.warning("يرجى إنشاء مشروع أولاً.")
