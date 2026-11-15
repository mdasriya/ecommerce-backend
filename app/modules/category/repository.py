from sqlalchemy.orm import Session, selectinload
from app.modules.category.model import Category
from sqlalchemy import select, func
import uuid



def create_category(db: Session, category_data: dict):
    category = Category(**category_data)
    db.add(category)
    db.commit()
    db.refresh(category) 
    return category

def get_category_by_slug(db: Session, slug: str):
    statement = select(Category).where(
        Category.slug == slug
    )
    result = db.execute(statement)
    return result.scalar_one_or_none()

def get_all_categories(db: Session):
    statement = select(Category)
    result = db.execute(statement)
    return result.scalars().all()

def get_category_by_id(
    db: Session,
    category_id: uuid.UUID
):
    statement = select(Category).where(
        Category.id == category_id
    )

    result = db.execute(statement)

    return result.scalar_one_or_none()

def update_category(db: Session, category: Category, update_data: dict):
    for field, value in update_data.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)

    return category

def delete_category(db:Session, category:Category):
    category.is_active = False
    db.commit()
    db.refresh(category)

    return category

def get_active_categories(db: Session):

    statement = select(Category).where(
        Category.is_active.is_(True)
    ).order_by(
        Category.sort_order.asc()
    )

    result = db.execute(statement)

    return result.scalars().all()

# Get active categories with active subcategories
def get_categories_with_subcategories(db: Session):

    statement = (
        select(Category)
        .where(
            Category.parent_id.is_(None),
            Category.is_active.is_(True)
        )
        .options(
            selectinload(Category.subcategories.and_(
                Category.is_active.is_(True)
            ))
        )
        .order_by(Category.sort_order.asc())
    )

    result = db.execute(statement)

    return result.scalars().all()

# Get categories with search, filter and pagination
def get_categories_paginated(
    db: Session,
    search: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10
):

    statement = select(Category)

    # Search by name or slug
    if search:
        search = search.strip()

        if search:
          search_term = f"%{search}%"

          statement = statement.where(
            Category.name.ilike(search_term) |
            Category.slug.ilike(search_term)
        )

    # Filter by active status
    if is_active is not None:
        statement = statement.where(
            Category.is_active.is_(is_active)
        )

    # Count matching records
    total_records = db.scalar(
        select(func.count()).select_from(statement.subquery())
    )

    # Calculate offset
    offset = (page - 1) * page_size

    # Apply pagination
    statement = (
        statement
        .order_by(Category.sort_order.asc(), Category.name.asc())
        .offset(offset)
        .limit(page_size)
    )

    result = db.execute(statement)

    categories = result.scalars().all()

    return categories, total_records