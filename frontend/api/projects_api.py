"""Projects related API calls"""

import requests
from frontend.config import API_BASE_URL

def create_project(name: str, location: str):
    return requests.post(
        f"{API_BASE_URL}/projects/",
        json={"name": name, "location": location},
    )

def add_boq_item(project_id: int, item_data: dict):
    return requests.post(
        f"{API_BASE_URL}/projects/{project_id}/boq",
        json=item_data,
    )
