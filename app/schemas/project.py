"""Project schemas"""

from pydantic import BaseModel
from typing import List, Optional


class ProjectCreate(BaseModel):
    """Schema for creating a project"""
    name: str
    location: Optional[str] = None


class ProjectRead(ProjectCreate):
    """Schema for reading a project"""
    id: int
    
    class Config:
        from_attributes = True
