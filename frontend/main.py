import sys
import os

# Add the parent directory to sys.path to allow imports from 'frontend' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from frontend.config import PAGE_TITLE, LAYOUT
from frontend.components.sidebar import render_sidebar
from frontend.views import projects_view, wizard_view, reports_view

# Page Config
st.set_page_config(page_title=PAGE_TITLE, layout=LAYOUT)

# Initialize Session State
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

# Render Sidebar
menu = render_sidebar()

# Routing
if menu == "1. تأسيس مشروع":
    projects_view.render_projects_view()
elif menu == "2. معالج رفع المستخلصات (Wizard)":
    wizard_view.render_wizard_view()
elif menu == "3. الاعتماد والتقارير":
    reports_view.render_reports_view()
