import uuid

from sqlalchemy import Boolean, CheckConstraint, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin
from app.modules.user.roles import UserRole


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # Defence in depth: the service always lower-cases emails, but this
        # guarantees that "John@x.com" and "john@x.com" can never both exist,
        # even if some future code path forgets to normalise.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # unique=True + index=True -> one UNIQUE index (fast login lookup and
    # duplicate protection enforced by the database itself).
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # Argon2id hash string (contains algorithm, parameters, salt and hash).
    # NEVER the plain password.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Stored as VARCHAR(20) + CHECK constraint (native_enum=False) instead of a
    # PostgreSQL ENUM type: much easier to extend with new roles later.
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="role",
            native_enum=False,
            create_constraint=True,
            length=20,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    def __repr__(self) -> str:
        # Deliberately excludes password_hash so it never ends up in logs.
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
