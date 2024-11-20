"""MongoDB error handling."""

from contextlib import asynccontextmanager

from pymongo.errors import DuplicateKeyError, OperationFailure
from stac_fastapi.types.errors import (
    ConflictError,
    DatabaseError,
    NotFoundError,
)

@asynccontextmanager
async def handle_mongodb_errors():
    """Context manager that translates MongoDB errors into FastAPI errors.

    Raises:
        ConflictError: On duplicate key errors
        NotFoundError: When document not found
        DatabaseError: On other MongoDB errors
    """
    try:
        yield
    except DuplicateKeyError as e:
        raise ConflictError(f"Duplicate key error: {str(e)}") from e
    except OperationFailure as e:
        if e.code == 96:
            raise NotFoundError(f"Document not found: {str(e)}") from e
        raise DatabaseError(f"Database operation failed: {str(e)}") from e
    except Exception as e:
        raise DatabaseError(f"Unexpected database error: {str(e)}") from e