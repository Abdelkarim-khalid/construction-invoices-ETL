"""Sidebar component"""

import streamlit as st

def render_sidebar():
    st.sidebar.title("القائمة الرئيسية")
    
    # Reset wizard state on page change
    def reset_wizard():
        st.session_state.step = 1
        st.session_state.uploaded_file = None
        st.session_state.sheet_civil = None
        st.session_state.sheet_elec = None

    menu = st.sidebar.radio(
        "تنقل بين الصفحات:",
        ["1. تأسيس مشروع", "2. معالج رفع المستخلصات (Wizard)", "3. الاعتماد والتقارير"],
        on_change=reset_wizard,
    )
    return menu
