from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
import uuid
import math
from app.modules.category import service
from app.core.response import success_response, error_response


def create_category(db: Session, category_data: dict):

    category = service.create_category(
        db,
        category_data
    )

    return success_response(
        message="Category created successfully",
        data=category
    )

def get_all_categories(db: Session):
    categories = service.get_all_categories(db)
    return success_response(
        message="Categories retrieved successfully",
        data=categories
    )

def get_category_by_id(
    db: Session,
    category_id: uuid.UUID
):

    category = service.get_category_by_id(
        db,
        category_id
    )

    return success_response(
        message="Category fetched successfully",
        data=category
    )

def update_category(
    db: Session,
    category_id: uuid.UUID,
    update_data: dict
):

    category = service.update_category(
        db,
        category_id,
        update_data
    )

    return success_response(
        message="Category updated successfully",
        data=category
    )

def delete_category(
    db: Session,
    category_id: uuid.UUID
):
    category = service.delete_category(
        db,
        category_id
    )

    return success_response(
        message="Category deleted successfully",
        data=category
    )

def get_active_categories(db: Session):

    categories = service.get_active_categories(db)

    return success_response(
        message="Active categories fetched successfully",
        data=categories
    )

# Get categories with subcategories
def get_categories_with_subcategories(db: Session):

    categories = service.get_categories_with_subcategories(db)

    return success_response(
        message="Categories fetched successfully",
        data=categories
    )

# Get categories with pagination
def get_categories_paginated(
    db: Session,
    search: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10
):

    categories, total_records = service.get_categories_paginated(
        db=db,
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size
    )

    total_pages = math.ceil(total_records / page_size)

    return success_response(
        message="Categories fetched successfully",
        data=categories,
        meta={
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages
        }
    )
