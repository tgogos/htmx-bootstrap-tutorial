# Standard library imports
from datetime import datetime, timezone
from typing import Optional

# Third-party imports
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DBItemBase(BaseModel):
    """Base model for DBItem with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    description: Optional[str] = Field(None, max_length=500, description="Item description")


class DBItemCreate(DBItemBase):
    """Model for creating a new database item."""
    pass


class DBItemUpdate(BaseModel):
    """Model for updating an existing database item."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Item name")
    description: Optional[str] = Field(None, max_length=500, description="Item description")


class DBItem(DBItemBase):
    """Complete database item model with all fields."""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    id: ObjectId = Field(default_factory=ObjectId, alias="_id", description="MongoDB document ID")
    created_at: datetime = Field(default_factory=utc_now, description="Item creation timestamp")
    updated_at: datetime = Field(default_factory=utc_now, description="Item last update timestamp")


class DBItemResponse(DBItemBase):
    """Database item model for API responses."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="MongoDB document ID as string")
    created_at: datetime = Field(..., description="Item creation timestamp")
    updated_at: datetime = Field(..., description="Item last update timestamp")


class PaginatedDBItems(BaseModel):
    """Paginated response model for database items."""
    items: list[DBItemResponse] = Field(..., description="List of database items")
    total_count: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
