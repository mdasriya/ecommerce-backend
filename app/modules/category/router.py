from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.modules.category import controller
from app.database.dependencies import get_db
from app.modules.category.schema import CategoryCreate, CategoryUpdate,CategoryWithSubcategoriesResponse, CategoryResponse
import uuid
from app.core.response import ApiResponse, PaginationMeta
from app.modules.auth.dependencies import require_staff

# Write operations require ADMIN or SUPER_ADMIN. GET endpoints stay public
# (the storefront needs them without login).
STAFF_ONLY = [Depends(require_staff)]


router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)

@router.post("/", dependencies=STAFF_ONLY)
def create_category(category_data: CategoryCreate,db:Session = Depends(get_db)):
    return controller.create_category(db, category_data.model_dump())

@router.get("/")
def get_all_categories(db: Session = Depends(get_db)):
    return controller.get_all_categories(db)

@router.get("/active")
def get_active_categories(
    db: Session = Depends(get_db)
):
    return controller.get_active_categories(db)

# Get categories with subcategories
@router.get(
    "/with-subcategories",
    response_model=ApiResponse[list[CategoryWithSubcategoriesResponse]]
)
def get_categories_with_subcategories(
    db: Session = Depends(get_db)
):
    return controller.get_categories_with_subcategories(db)

@router.get("/paginated", response_model=ApiResponse[list[CategoryResponse]])
def get_categories_paginated(
    search: str | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return controller.get_categories_paginated(
        db=db,
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size
    )



@router.get("/{category_id}")
def get_category_by_id(
    category_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    return controller.get_category_by_id(
        db,
        category_id
    )

@router.patch("/{category_id}", dependencies=STAFF_ONLY)
def update_category(
    category_id: uuid.UUID,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db)
):
    update_data = category_data.model_dump(
        exclude_unset=True
    )

    return controller.update_category(
        db,
        category_id,
        update_data
    )

@router.delete("/{category_id}", dependencies=STAFF_ONLY)
def delete_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    return controller.delete_category(
        db,
        category_id
    )





