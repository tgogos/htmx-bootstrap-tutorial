"""Pydantic schemas for books API."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

BookCategory = Literal[
    "fiction",
    "nonfiction",
    "scifi",
    "fantasy",
    "mystery",
    "biography",
    "other",
]


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=200)
    year: Optional[int] = Field(None, ge=0, le=9999)
    notes: Optional[str] = Field(None, max_length=2000)
    category: BookCategory = "other"
    isbn: Optional[str] = Field(None, max_length=32)
    page_count: Optional[int] = Field(None, ge=1, le=100_000)
    available: bool = True


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=200)
    year: Optional[int] = Field(None, ge=0, le=9999)
    notes: Optional[str] = Field(None, max_length=2000)
    category: Optional[BookCategory] = None
    isbn: Optional[str] = Field(None, max_length=32)
    page_count: Optional[int] = Field(None, ge=1, le=100_000)
    available: Optional[bool] = None


class BookResponse(BookBase):
    id: str
    added_by_user_id: Optional[int] = None
    added_by_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaginatedBooks(BaseModel):
    items: list[BookResponse]
    total_count: int
    page: int
    size: int
    total_pages: int
