import uuid

from sqlalchemy import String, ForeignKey, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    slug: Mapped[str] = mapped_column(
        String(180),
        unique=True,
        nullable=False,
        index=True
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True
    )

    # Relationship with parent category
    parent = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="subcategories"
    )

    # Relationship with child categories
    subcategories = relationship(
        "Category",
        back_populates="parent"
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    banner_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    show_in_menu: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )