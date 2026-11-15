
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_records: int
    total_pages: int


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None
    meta: PaginationMeta | dict | None = None
    errors: dict | None = None


def success_response(
    message: str,
    data=None,
    meta=None
):
    return {
        "success": True,
        "message": message,
        "data": data,
        "meta": meta,
        "errors": None
    }


def error_response(
    message: str,
    errors=None
):
    return {
        "success": False,
        "message": message,
        "data": None,
        "meta": None,
        "errors": errors
    }
