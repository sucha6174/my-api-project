import os
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Any, List
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from src.database import init_db, get_db, Message

logger = logging.getLogger("api.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager that performs database startup checks and initialization.
    """
    logger.info("Starting up application and initializing database connection...")
    init_db()
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="Resilient REST API",
    description="A highly available, containerized REST API with automated cloud deployment.",
    version="1.0.0",
    lifespan=lifespan
)


# Schemas
class MessageRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The content of the message (1 to 255 characters)"
    )


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    text: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: List[Any]


# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Overrides the default FastAPI 422 Unprocessable Entity with a standardized
    400 Bad Request response containing clear validation error details.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Bad Request",
            "message": "Invalid input data provided.",
            "details": exc.errors()
        }
    )


# Endpoints
@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    tags=["Monitoring"]
)
def get_health():
    """
    Health check endpoint utilized by load balancers and container orchestrators.
    """
    return {"status": "healthy"}


@app.get(
    "/greet/{name}",
    status_code=status.HTTP_200_OK,
    summary="Greet by Name",
    tags=["Greeting"]
)
def greet(name: str):
    """
    Dynamic greeting endpoint demonstrating path parameter extraction and formatting.
    """
    return {"message": f"Hello, {name}!"}


@app.post(
    "/message",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    },
    summary="Create Message",
    tags=["Messages"]
)
def create_message(payload: MessageRequest, db: Session = Depends(get_db)):
    """
    Persists a valid message payload to the PostgreSQL database and returns the generated UUID.
    """
    try:
        db_message = Message(text=payload.text)
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message
    except Exception as exc:
        db.rollback()
        logger.error(f"Error persisting message to database: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(exc)}"
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("src.app:app", host="0.0.0.0", port=port)
