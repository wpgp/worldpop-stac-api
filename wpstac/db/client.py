"""MongoDB client and connection handling."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

from .errors import DatabaseError

async def connect_to_db(app: FastAPI) -> None:
    """Create MongoDB client and store it in the application state.

    Args:
        app: FastAPI application instance

    Raises:
        DatabaseError: If connection to MongoDB fails
    """
    settings = app.state.settings
    try:
        client = AsyncIOMotorClient(
            settings.mongodb_connection_string,
            serverSelectionTimeoutMS=5000
        )
        await client.admin.command('ping')
        app.state.motor_client = client
        app.state.database = client[settings.mongodb_dbname]
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        raise DatabaseError(f"Failed to connect to MongoDB: {str(e)}")

async def close_db_connection(app: FastAPI) -> None:
    """Close MongoDB client safely.

    Args:
        app: FastAPI application instance
    """
    if hasattr(app.state, 'motor_client'):
        app.state.motor_client.close()

@asynccontextmanager
async def get_connection(request: Request) -> AsyncIterator[AsyncIOMotorClient]:
    """Get MongoDB client from the application state.

    Args:
        request: FastAPI request object

    Yields:
        AsyncIOMotorClient: MongoDB client instance

    Raises:
        DatabaseError: If client is not initialized
    """
    if not hasattr(request.app.state, 'motor_client'):
        raise DatabaseError("Database connection not initialized")
    try:
        yield request.app.state.motor_client
    except Exception as e:
        raise DatabaseError(f"Database operation failed: {str(e)}")

async def check_db_health(app: FastAPI) -> bool:
    try:
        await app.state.motor_client.admin.command('ping')
        return True
    except Exception:
        return False