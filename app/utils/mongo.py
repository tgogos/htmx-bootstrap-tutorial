# Standard library imports
import logging
from typing import Optional

# Third-party imports
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError, OperationFailure

# Local imports
from app.core import config

logger = logging.getLogger(__name__)

# Global database connection
client: Optional[AsyncIOMotorClient] = None
database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    """
    Create database connection to MongoDB.
    
    Raises:
        ConnectionFailure: If unable to connect to MongoDB
        ServerSelectionTimeoutError: If MongoDB server is not available
    """
    global client, database
    
    try:
        # Create MongoDB client
        client = AsyncIOMotorClient(
            config.MONGO_URI,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        
        # Test the connection
        await client.admin.command('ping')
        
        # Get database
        database = client[config.MONGO_DATABASE]
        
        logger.info(
            "Connected to MongoDB at %s:%s",
            config.MONGO_HOST,
            config.MONGO_PORT,
        )
        
    except ConnectionFailure:
        logger.exception("MongoDB connection failed")
        raise
    except ServerSelectionTimeoutError:
        logger.exception("MongoDB server selection timeout")
        raise
    except Exception:
        logger.exception("Unexpected MongoDB connection error")
        raise


async def close_mongo_connection() -> None:
    """Close database connection to MongoDB."""
    global client
    
    if client:
        client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """
    Get the database instance.
    
    Returns:
        AsyncIOMotorDatabase: The database instance
        
    Raises:
        RuntimeError: If database is not connected
    """
    if database is None:
        raise RuntimeError("Database not connected. Call connect_to_mongo() first.")
    return database


def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    """
    Get a collection from the database.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        AsyncIOMotorCollection: The collection instance
        
    Raises:
        RuntimeError: If database is not connected
    """
    db = get_database()
    return db[collection_name]


async def check_database_connection() -> bool:
    """
    Check if the database connection is healthy.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        if client is None:
            return False
        
        # Ping the database
        await client.admin.command('ping')
        return True
        
    except Exception:
        return False


class MongoDBError(Exception):
    """Base exception for MongoDB operations."""
    pass


class MongoDBConnectionError(MongoDBError):
    """Raised when MongoDB connection fails."""
    pass


class MongoDBOperationError(MongoDBError):
    """Raised when MongoDB operation fails."""
    pass


class MongoDBDuplicateKeyError(MongoDBError):
    """Raised when trying to insert a document with duplicate key."""
    pass


def handle_mongo_error(error: Exception) -> MongoDBError:
    """
    Convert MongoDB exceptions to custom exceptions.
    
    Args:
        error: The original MongoDB exception
        
    Returns:
        MongoDBError: Custom MongoDB exception
    """
    if isinstance(error, ConnectionFailure):
        return MongoDBConnectionError(f"Database connection failed: {str(error)}")
    elif isinstance(error, ServerSelectionTimeoutError):
        return MongoDBConnectionError(f"Database server not available: {str(error)}")
    elif isinstance(error, DuplicateKeyError):
        return MongoDBDuplicateKeyError(f"Duplicate key error: {str(error)}")
    elif isinstance(error, OperationFailure):
        return MongoDBOperationError(f"Database operation failed: {str(error)}")
    else:
        return MongoDBOperationError(f"Unexpected database error: {str(error)}")
