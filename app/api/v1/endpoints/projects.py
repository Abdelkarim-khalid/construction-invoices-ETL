"""Projects API endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.project import ProjectCreate, ProjectRead
from app.schemas.boq import BOQItemCreate, BOQItemRead
from app.services import projects_service, boq_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    """
    الحصول على قائمة كل المشاريع
    """
    projects = projects_service.get_projects(db)
    return projects


@router.post("/", response_model=ProjectRead)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """
    إنشاء مشروع جديد
    """
    new_project = projects_service.create_project(db, project)
    return new_project


@router.post("/{project_id}/boq", response_model=BOQItemRead)
def add_boq_item(
    project_id: int,
    item: BOQItemCreate,
    db: Session = Depends(get_db)
):
    """
    إضافة بند BOQ لمشروع
    """
    try:
        new_item = boq_service.add_boq_item(db, project_id, item)
        return new_item
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{project_id}/boq", response_model=List[BOQItemRead])
def get_boq_items(project_id: int, db: Session = Depends(get_db)):
    """
    الحصول على بنود BOQ لمشروع
    """
    items = boq_service.get_boq_items(db, project_id)
    return items
