"""Common schemas used across the application"""

from pydantic import BaseModel
from enum import Enum


class Message(BaseModel):
    """Generic message response"""
    message: str


class InvoiceStatusEnum(str, Enum):
    """Invoice status enum for API"""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
