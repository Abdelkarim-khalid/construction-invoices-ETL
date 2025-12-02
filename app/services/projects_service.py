"""Projects service - Business logic for project management"""

from typing import List
from sqlalchemy.orm import Session

from app.models import Project
from app.schemas.project import ProjectCreate


def create_project(db: Session, project: ProjectCreate) -> Project:
    """
    إنشاء مشروع جديد
    
    Args:
        db: Database session
        project: بيانات المشروع الجديد
        
    Returns:
        Project: المشروع المُنشأ
    """
    new_project = Project(
        name=project.name,
        location=project.location
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


def get_projects(db: Session) -> List[Project]:
    """
    الحصول على قائمة كل المشاريع
    
    Args:
        db: Database session
        
    Returns:
        List[Project]: قائمة المشاريع
    """
    return db.query(Project).all()


def get_project_by_id(db: Session, project_id: int) -> Project | None:
    """
    الحصول على مشروع بالـ ID
    
    Args:
        db: Database session
        project_id: معرّف المشروع
        
    Returns:
        Project | None: المشروع أو None إذا لم يتم العثور عليه
    """
    return db.query(Project).filter(Project.id == project_id).first()
