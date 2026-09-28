# Standard library imports
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

# Third-party imports
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ItemBase(BaseModel):
    """Base model for Item with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    description: Optional[str] = Field(None, max_length=500, description="Item description")


class ItemCreate(ItemBase):
    """Model for creating a new item."""
    pass


class ItemUpdate(BaseModel):
    """Model for updating an existing item."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Item name")
    description: Optional[str] = Field(None, max_length=500, description="Item description")


class Item(ItemBase):
    """Complete Item model with all fields."""
    id: UUID = Field(default_factory=uuid4, description="Unique item identifier")
    created_at: datetime = Field(default_factory=utc_now, description="Item creation timestamp")
    updated_at: datetime = Field(default_factory=utc_now, description="Item last update timestamp")


class ItemResponse(Item):
    """Item model for API responses."""
    pass


class PaginatedItems(BaseModel):
    """Paginated response model for items."""
    items: list[ItemResponse] = Field(..., description="List of items")
    total_count: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
