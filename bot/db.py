from datetime import datetime, timezone

from custom_types import TicketDict, status_type
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship, sessionmaker

import settings as setting


class Base(MappedAsDataclass, DeclarativeBase, repr=False, unsafe_hash=True, kw_only=True):
    """
    Base for SQLAlchemy dataclass
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)


class User(Base, sessionmaker):
    __tablename__ = "users"
    user_uid: Mapped[int] = mapped_column(Integer, unique=True)
    first_name: Mapped[str] = mapped_column(String(30))
    last_name: Mapped[str] = mapped_column(String(30))
    department: Mapped[str] = mapped_column(String(50))
    is_priority: Mapped[int] = mapped_column(Integer)

    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="user", init=False)

    def __repr__(self) -> str:
        return (
            f"User=(id={self.id!s}, first_name={self.first_name!s}, last_name={self.last_name!s},"
            f"department={self.department!s}, is_priority={self.is_priority!s})"
        )


class BlockedUser(Base, sessionmaker):
    __tablename__ = "blocked_users"
    user_uid: Mapped[int] = mapped_column(Integer)
    username: Mapped[str] = mapped_column(String)


class Ticket(Base, sessionmaker):
    __tablename__ = "tickets"
    user_uid: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_uid"))
    user: Mapped["User"] = relationship("User", back_populates="tickets", init=False)
    title: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[status_type] = mapped_column(String)
    update_reason: Mapped[str | None] = mapped_column(String, nullable=True, init=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.now(tz=timezone.utc))
    dates_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(tz=timezone.utc))

    def __repr__(self) -> str:
        return (
            f"User(user_id={self.user_uid} title={self.title!r}, description={self.description!r},"
            f"status = {self.status})"
        )

    def as_ticket_dict(self) -> TicketDict:
        return TicketDict(user_uid=self.user_uid, title=self.title, description=self.description, status=self.status)


#engine = create_engine("sqlite:///bot.db", echo=True)
engine = create_engine(setting.engine, echo=True)

Base.metadata.create_all(engine)
Session = sessionmaker(autoflush=False, bind=engine)
