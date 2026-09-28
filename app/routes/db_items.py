# Standard library imports
from datetime import datetime, timezone
from typing import List

# Third-party imports
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from bson.errors import InvalidId

# Local imports
from app.models.db_item import DBItem, DBItemCreate, DBItemUpdate, DBItemResponse, PaginatedDBItems
from app.utils.mongo import get_collection, handle_mongo_error, MongoDBError, MongoDBConnectionError, MongoDBOperationError

router = APIRouter()


@router.post("/", 
    response_model=DBItemResponse,
    status_code=201,
    summary="Create a new database item",
    response_description="The created database item"
)
async def create_db_item(item: DBItemCreate) -> DBItemResponse:
    """
    Create a new item in MongoDB.
    
    Args:
        item: Item data for creation
        
    Returns:
        DBItemResponse: The created item
        
    Raises:
        HTTPException: If item creation fails
    """
    try:
        # Get collection
        collection = get_collection("db_items")
        
        # Create new item
        new_item = DBItem(
            name=item.name,
            description=item.description
        )
        
        # Convert to dict for MongoDB insertion
        item_dict = new_item.model_dump(by_alias=True, exclude={"id"})
        
        # Insert into MongoDB
        result = await collection.insert_one(item_dict)
        
        # Get the inserted document
        inserted_item = await collection.find_one({"_id": result.inserted_id})
        
        # Convert to response model
        response_item = DBItemResponse(
            id=str(inserted_item["_id"]),
            name=inserted_item["name"],
            description=inserted_item.get("description"),
            created_at=inserted_item["created_at"],
            updated_at=inserted_item["updated_at"]
        )
        
        return response_item
    
    except MongoDBError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create item: {str(e)}"
        )


@router.get("/", 
    response_model=PaginatedDBItems,
    summary="Get all database items with pagination",
    response_description="Paginated list of database items"
)
async def get_db_items(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page")
) -> PaginatedDBItems:
    """
    Get all items from MongoDB with pagination.
    
    Args:
        page: Page number (starts from 1)
        size: Number of items per page (max 100)
        
    Returns:
        PaginatedDBItems: Paginated list of items
    """
    try:
        # Get collection
        collection = get_collection("db_items")
        
        # Get total count
        total_count = await collection.count_documents({})
        total_pages = (total_count + size - 1) // size
        
        # Calculate pagination
        skip = (page - 1) * size
        
        # Get items with pagination, sorted by created_at descending
        cursor = collection.find({}).sort("created_at", -1).skip(skip).limit(size)
        items = await cursor.to_list(length=size)
        
        # Convert to response models
        item_responses = []
        for item in items:
            response_item = DBItemResponse(
                id=str(item["_id"]),
                name=item["name"],
                description=item.get("description"),
                created_at=item["created_at"],
                updated_at=item["updated_at"]
            )
            item_responses.append(response_item)
        
        return PaginatedDBItems(
            items=item_responses,
            total_count=total_count,
            page=page,
            size=size,
            total_pages=total_pages
        )
    
    except MongoDBError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve items: {str(e)}"
        )


@router.get("/{item_id}", 
    response_model=DBItemResponse,
    summary="Get database item by ID",
    response_description="The requested database item"
)
async def get_db_item(item_id: str) -> DBItemResponse:
    """
    Get a specific item from MongoDB by its ID.
    
    Args:
        item_id: The MongoDB ObjectId as string
        
    Returns:
        DBItemResponse: The requested item
        
    Raises:
        HTTPException: If item is not found or ID is invalid
    """
    try:
        # Validate ObjectId
        try:
            object_id = ObjectId(item_id)
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid item ID format: {item_id}"
            )
        
        # Get collection
        collection = get_collection("db_items")
        
        # Find item by ID
        item = await collection.find_one({"_id": object_id})
        
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Item with id {item_id} not found"
            )
        
        # Convert to response model
        response_item = DBItemResponse(
            id=str(item["_id"]),
            name=item["name"],
            description=item.get("description"),
            created_at=item["created_at"],
            updated_at=item["updated_at"]
        )
        
        return response_item
    
    except HTTPException:
        raise
    except MongoDBError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve item: {str(e)}"
        )


@router.put("/{item_id}", 
    response_model=DBItemResponse,
    summary="Update a database item",
    response_description="The updated database item"
)
async def update_db_item(item_id: str, item_update: DBItemUpdate) -> DBItemResponse:
    """
    Update an existing item in MongoDB.
    
    Args:
        item_id: The MongoDB ObjectId as string
        item_update: Updated item data
        
    Returns:
        DBItemResponse: The updated item
        
    Raises:
        HTTPException: If item is not found or update fails
    """
    try:
        # Validate ObjectId
        try:
            object_id = ObjectId(item_id)
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid item ID format: {item_id}"
            )
        
        # Get collection
        collection = get_collection("db_items")
        
        # Check if item exists
        existing_item = await collection.find_one({"_id": object_id})
        if existing_item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Item with id {item_id} not found"
            )
        
        # Prepare update data
        update_data = item_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Update the item
        result = await collection.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to update item"
            )
        
        # Get the updated item
        updated_item = await collection.find_one({"_id": object_id})
        
        # Convert to response model
        response_item = DBItemResponse(
            id=str(updated_item["_id"]),
            name=updated_item["name"],
            description=updated_item.get("description"),
            created_at=updated_item["created_at"],
            updated_at=updated_item["updated_at"]
        )
        
        return response_item
    
    except HTTPException:
        raise
    except MongoDBError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update item: {str(e)}"
        )


@router.delete("/{item_id}", 
    status_code=204,
    summary="Delete a database item",
    response_description="Item deleted successfully"
)
async def delete_db_item(item_id: str) -> None:
    """
    Delete an item from MongoDB by its ID.
    
    Args:
        item_id: The MongoDB ObjectId as string
        
    Raises:
        HTTPException: If item is not found or deletion fails
    """
    try:
        # Validate ObjectId
        try:
            object_id = ObjectId(item_id)
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid item ID format: {item_id}"
            )
        
        # Get collection
        collection = get_collection("db_items")
        
        # Check if item exists
        existing_item = await collection.find_one({"_id": object_id})
        if existing_item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Item with id {item_id} not found"
            )
        
        # Delete the item
        result = await collection.delete_one({"_id": object_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete item"
            )
        
        # Return 204 No Content
        return None
    
    except HTTPException:
        raise
    except MongoDBError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete item: {str(e)}"
        )


@router.get("/search/", 
    response_model=PaginatedDBItems,
    summary="Search database items by name",
    response_description="Paginated list of matching database items"
)
async def search_db_items(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page")
) -> PaginatedDBItems:
    """
    Search items in MongoDB by name (case-insensitive).
    
    Args:
        q: Search query
        page: Page number (starts from 1)
        size: Number of items per page (max 100)
        
    Returns:
        PaginatedDBItems: Paginated list of matching items
    """
    try:
        # Get collection
        collection = get_collection("db_items")
        
        # Create search query (case-insensitive)
        search_query = {"name": {"$regex": q, "$options": "i"}}
        
        # Get total count
        total_count = await collection.count_documents(search_query)
        total_pages = (total_count + size - 1) // size
        
        # Calculate pagination
        skip = (page - 1) * size
        
        # Search items with pagination, sorted by created_at descending
        cursor = collection.find(search_query).sort("created_at", -1).skip(skip).limit(size)
        items = await cursor.to_list(length=size)
        
        # Convert to response models
        item_responses = []
        for item in items:
            response_item = DBItemResponse(
                id=str(item["_id"]),
                name=item["name"],
                description=item.get("description"),
                created_at=item["created_at"],
                updated_at=item["updated_at"]
            )
            item_responses.append(response_item)
        
        return PaginatedDBItems(
            items=item_responses,
            total_count=total_count,
            page=page,
            size=size,
            total_pages=total_pages
        )
    
    except MongoDBError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search items: {str(e)}"
        )
