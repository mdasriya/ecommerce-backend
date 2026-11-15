from sqlalchemy.orm import Session
from app.modules.category.model import Category
from app.modules.category import repository
from app.core.exceptions import AppException
import uuid

class CategoryAlreadyExistsError(Exception):
    pass

# create category
def create_category(db: Session, category_data: dict):

    existing_category = repository.get_category_by_slug(
        db,
        category_data['slug']
    )

    if existing_category:
        raise AppException(
            message=f"Category with slug '{category_data['slug']}' already exists.",
            status_code=409
        )

    # Validate parent category
    parent_id = category_data.get("parent_id")

    if parent_id is not None:
        parent_category = repository.get_category_by_id(
            db,
            parent_id
        )

        if not parent_category:
            raise AppException(
                message="Parent category not found.",
                status_code=404
            )

    # Create category
    return repository.create_category(
        db,
        category_data
    )
# get all category data
def get_all_categories(db: Session):
    return repository.get_all_categories(db)

# get single category data by ID
def get_category_by_id(db: Session,category_id: uuid.UUID):
    category = repository.get_category_by_id(
        db,
        category_id
    )

    if not category:
        raise AppException(
            message="Category not found",
            status_code=404
        )

    return category





def update_category(
    db: Session,
    category_id: uuid.UUID,
    update_data: dict
):
    category = repository.get_category_by_id(
        db,
        category_id
    )

    if not category:
        raise AppException(
            message="Category not found",
            status_code=404
        )

    # Validate duplicate slug
    if "slug" in update_data:
        existing_category = repository.get_category_by_slug(
            db,
            update_data["slug"]
        )

        if existing_category and existing_category.id != category.id:
            raise AppException(
                message="Category slug already exists",
                status_code=409
            )

    # Validate parent category
    if "parent_id" in update_data:

        parent_id = update_data["parent_id"]

        if parent_id is not None:

            parent_category = repository.get_category_by_id(
                db,
                parent_id
            )

            if not parent_category:
                raise AppException(
                    message="Parent category not found.",
                    status_code=404
                )

            # Prevent assigning an inactive parent
            if not parent_category.is_active:
                raise AppException(
                    message="Cannot assign an inactive category as a parent.",
                    status_code=400
                )

            # Prevent category from becoming its own parent
            if parent_category.id == category.id:
                raise AppException(
                    message="A category cannot be its own parent.",
                    status_code=400
                )

            # Only parent categories can have subcategories
            if parent_category.parent_id is not None:
                raise AppException(
                    message="Subcategories cannot have another subcategory as their parent.",
                    status_code=400
                )

    # Prevent parent category from becoming a subcategory
    if "parent_id" in update_data and update_data["parent_id"] is not None:

        if category.parent_id is None and category.subcategories:
            raise AppException(
                message="A parent category with subcategories cannot become a subcategory.",
                status_code=400
            )

    # Prevent deactivating a parent with active subcategories
    if update_data.get("is_active") is False:

        active_subcategories = [
            subcategory
            for subcategory in category.subcategories
            if subcategory.is_active
        ]

        if active_subcategories:
            raise AppException(
                message="Cannot deactivate category while it has active subcategories.",
                status_code=400
            )

    # Update category
    return repository.update_category(
        db,
        category,
        update_data
    )


# delete category 
def delete_category(db: Session, category_id: uuid.UUID):

    category = repository.get_category_by_id(
        db,
        category_id
    )

    if not category:
        raise AppException(
            message="Category not found",
            status_code=404
        )

    # Prevent deactivating parent with active subcategories
    active_subcategories = [
        subcategory
        for subcategory in category.subcategories
        if subcategory.is_active
    ]

    if active_subcategories:
        raise AppException(
            message="Cannot deactivate category while it has active subcategories.",
            status_code=400
        )

    # Deactivate category
    return repository.delete_category(
        db,
        category
    )

def get_active_categories(db: Session):

    return repository.get_active_categories(db)

# Get categories with subcategories
def get_categories_with_subcategories(db: Session):

    categories = repository.get_categories_with_subcategories(db)

    return categories

# Get categories with pagination
def get_categories_paginated(
    db: Session,
    search: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10
):

    categories, total_records = repository.get_categories_paginated(
        db=db,
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size
    )

    return categories, total_records