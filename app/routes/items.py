# Standard library imports
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID, uuid4

# Third-party imports
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

# Local imports
from app.models.item import Item, ItemCreate, ItemUpdate, ItemResponse, PaginatedItems

# In-memory storage for items
items_storage: Dict[UUID, Item] = {}

router = APIRouter()


@router.post("/", 
    response_model=ItemResponse,
    status_code=201,
    summary="Create a new item",
    response_description="The created item"
)
async def create_item(item: ItemCreate) -> ItemResponse:
    """
    Create a new item.
    
    Args:
        item: Item data for creation
        
    Returns:
        ItemResponse: The created item
        
    Raises:
        HTTPException: If item creation fails
    """
    try:
        # Create new item
        new_item = Item(
            name=item.name,
            description=item.description
        )
        
        # Store in memory
        items_storage[new_item.id] = new_item
        
        return ItemResponse(**new_item.model_dump())
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create item: {str(e)}"
        )


@router.get("/", 
    response_model=PaginatedItems,
    summary="Get all items with pagination",
    response_description="Paginated list of items"
)
async def get_items(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page")
) -> PaginatedItems:
    """
    Get all items with pagination.
    
    Args:
        page: Page number (starts from 1)
        size: Number of items per page (max 100)
        
    Returns:
        PaginatedItems: Paginated list of items
    """
    try:
        # Convert dict to list and sort by created_at
        all_items = sorted(
            items_storage.values(), 
            key=lambda x: x.created_at, 
            reverse=True
        )
        
        total_count = len(all_items)
        total_pages = (total_count + size - 1) // size
        
        # Calculate pagination
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_items = all_items[start_idx:end_idx]
        
        # Convert to response models
        item_responses = [ItemResponse(**item.model_dump()) for item in paginated_items]
        
        return PaginatedItems(
            items=item_responses,
            total_count=total_count,
            page=page,
            size=size,
            total_pages=total_pages
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve items: {str(e)}"
        )


@router.get("/{item_id}", 
    response_model=ItemResponse,
    summary="Get item by ID",
    response_description="The requested item"
)
async def get_item(item_id: UUID) -> ItemResponse:
    """
    Get a specific item by its ID.
    
    Args:
        item_id: The unique identifier of the item
        
    Returns:
        ItemResponse: The requested item
        
    Raises:
        HTTPException: If item is not found
    """
    if item_id not in items_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Item with id {item_id} not found"
        )
    
    item = items_storage[item_id]
    return ItemResponse(**item.model_dump())


@router.put("/{item_id}", 
    response_model=ItemResponse,
    summary="Update an item",
    response_description="The updated item"
)
async def update_item(item_id: UUID, item_update: ItemUpdate) -> ItemResponse:
    """
    Update an existing item.
    
    Args:
        item_id: The unique identifier of the item
        item_update: Updated item data
        
    Returns:
        ItemResponse: The updated item
        
    Raises:
        HTTPException: If item is not found or update fails
    """
    if item_id not in items_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Item with id {item_id} not found"
        )
    
    try:
        # Get existing item
        existing_item = items_storage[item_id]
        
        # Update fields if provided
        update_data = item_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )
        
        # Update the item
        for field, value in update_data.items():
            setattr(existing_item, field, value)
        
        # Update timestamp
        existing_item.updated_at = datetime.now(timezone.utc)
        
        # Store updated item
        items_storage[item_id] = existing_item
        
        return ItemResponse(**existing_item.model_dump())
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update item: {str(e)}"
        )


@router.delete("/{item_id}", 
    status_code=204,
    summary="Delete an item",
    response_description="Item deleted successfully"
)
async def delete_item(item_id: UUID) -> None:
    """
    Delete an item by its ID.
    
    Args:
        item_id: The unique identifier of the item
        
    Raises:
        HTTPException: If item is not found or deletion fails
    """
    if item_id not in items_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Item with id {item_id} not found"
        )
    
    try:
        # Remove from storage
        del items_storage[item_id]
        
        # Return 204 No Content - just return None, FastAPI handles the status code
        return None
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete item: {str(e)}"
        )


@router.get("/search/", 
    response_model=PaginatedItems,
    summary="Search items by name",
    response_description="Paginated list of matching items"
)
async def search_items(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page")
) -> PaginatedItems:
    """
    Search items by name (case-insensitive).
    
    Args:
        q: Search query
        page: Page number (starts from 1)
        size: Number of items per page (max 100)
        
    Returns:
        PaginatedItems: Paginated list of matching items
    """
    try:
        # Filter items by name (case-insensitive)
        matching_items = [
            item for item in items_storage.values()
            if q.lower() in item.name.lower()
        ]
        
        # Sort by created_at
        matching_items.sort(key=lambda x: x.created_at, reverse=True)
        
        total_count = len(matching_items)
        total_pages = (total_count + size - 1) // size
        
        # Calculate pagination
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_items = matching_items[start_idx:end_idx]
        
        # Convert to response models
        item_responses = [ItemResponse(**item.model_dump()) for item in paginated_items]
        
        return PaginatedItems(
            items=item_responses,
            total_count=total_count,
            page=page,
            size=size,
            total_pages=total_pages
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search items: {str(e)}"
        )
