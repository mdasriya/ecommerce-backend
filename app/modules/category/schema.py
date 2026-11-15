from pydantic import BaseModel, field_validator
from uuid import UUID


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    parent_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Category name cannot be empty.")

        return value

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value):
        value = value.strip().lower()

        if not value:
            raise ValueError("Category slug cannot be empty.")

        if " " in value:
            raise ValueError("Slug cannot contain spaces.")

        return value



class CategoryUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    image_url: str | None = None
    banner_image_url: str | None = None
    is_active: bool | None = None
    show_in_menu: bool | None = None
    is_featured: bool | None = None
    sort_order: int | None = None
    parent_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if value is None:
            raise ValueError("Category name cannot be null.")

        value = value.strip()

        if not value:
            raise ValueError("Category name cannot be empty.")

        return value

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value):
        if value is None:
            raise ValueError("Category slug cannot be null.")

        value = value.strip().lower()

        if not value:
            raise ValueError("Category slug cannot be empty.")

        if " " in value:
            raise ValueError("Slug cannot contain spaces.")

        return value


class CategoryResponse(BaseModel):
    # UUID (not str): the database returns uuid.UUID objects. FastAPI
    # still serialises them to strings in the JSON response.
    id: UUID
    name: str
    slug: str
    description: str | None
    image_url: str | None
    banner_image_url: str | None
    parent_id: UUID | None
    is_active: bool
    show_in_menu: bool
    is_featured: bool
    sort_order: int

    # Allows building this schema from a SQLAlchemy object.
    model_config = {"from_attributes": True}


class SubcategoryResponse(BaseModel):
    id: UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


class CategoryWithSubcategoriesResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    subcategories: list[SubcategoryResponse]

    model_config = {"from_attributes": True}

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_records: int
    total_pages: int