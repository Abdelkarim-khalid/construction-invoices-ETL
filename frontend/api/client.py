"""Base API client and common requests"""

import requests
import streamlit as st
from frontend.config import API_BASE_URL

def fetch_projects_list():
    """Fetch all projects and return a dict mapping 'Name (ID)' -> ID"""
    try:
        res = requests.get(f"{API_BASE_URL}/projects/")
        if res.status_code == 200:
            return {f"{p['name']} (ID: {p['id']})": p["id"] for p in res.json()}
        return {}
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return {}
