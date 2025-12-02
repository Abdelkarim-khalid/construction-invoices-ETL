"""Invoices related API calls"""

import requests
from frontend.config import API_BASE_URL

def upload_invoice(files, data):
    return requests.post(
        f"{API_BASE_URL}/invoices/upload",
        files=files,
        data=data,
    )

def get_staging_data(invoice_id: int):
    return requests.get(f"{API_BASE_URL}/invoices/{invoice_id}/staging")

def update_staging_data(invoice_id: int, payload: list):
    return requests.put(
        f"{API_BASE_URL}/invoices/{invoice_id}/staging",
        json=payload,
    )

def approve_invoice(invoice_id: int):
    return requests.post(f"{API_BASE_URL}/invoices/{invoice_id}/approve")

def get_schedule_report(project_id: int, month: int, year: int):
    return requests.get(
        f"{API_BASE_URL}/reports/schedule/{project_id}",
        params={"month": month, "year": year},
    )
