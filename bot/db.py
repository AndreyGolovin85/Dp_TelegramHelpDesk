from sqlalchemy import Integer, String, Text, create_engine, select, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from custom_types import UserDict, TicketDict


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_uid = mapped_column(Integer)
    first_name: Mapped[str] = mapped_column(String(30))
    last_name: Mapped[str] = mapped_column(String(30))
    department: Mapped[str] = mapped_column(String(50))
    is_priority: Mapped[int] = mapped_column(Integer)

    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="user")

    def __repr__(self) -> str:
        return f"User=(id={self.id!s}, first_name={self.first_name!s}, last_name={self.last_name!s}," \
               f"department={self.department!s}, is_priority={self.is_priority!s})"

    @classmethod
    def add_user(cls, user_dict: UserDict):
        with Session() as session:
            new_user = User(
                user_uid=user_dict.user_uid,
                first_name=user_dict.first_name,
                last_name=user_dict.last_name,
                department=user_dict.department,
                is_priority=user_dict.is_priority
            )
            session.add(new_user)
            session.commit()
            return new_user

    @classmethod
    def get_user_by_uid(cls, user_uid: int):
        with Session() as session:
            return session.query(User).filter_by(user_uid=user_uid).first()


class Ticket(Base, sessionmaker):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String['new', 'in_work', 'completed', 'rejected'])
    datess = mapped_column(DateTime, default=datetime.utcnow)
    last_updated: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.utcnow())

    user_uid: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_uid"))
    user: Mapped["User"] = relationship("User", back_populates="tickets")

    def __repr__(self) -> str:
        return f"User(user_id={self.user_uid} title={self.title!r}, description={self.description!r}," \
               f"status = {self.status})"

    @classmethod
    def list_tickets(cls, uid=0, status: str | None = None) -> list[TicketDict]:
        """Возвращает список словарей тикетов"""
        tickets_dict = []
        with Session() as session:
            if uid != 0:
                select_tickets = select(Ticket).where(uid == Ticket.user_uid)
            elif status is None:
                select_tickets = select(Ticket)
            else:
                select_tickets = select(Ticket).where(status == Ticket.status)

            for ticket in session.query(select_tickets.subquery()).all():
                tickets_dict.append(TicketDict(ticket.user_uid, ticket.title, ticket.description, ticket.status))
        return tickets_dict

    @classmethod
    def get_ticket_by_id(cls, ticket_id: int):
        """Получает тикет из базы данных по его id."""
        with Session() as session:
            ticket = session.query(Ticket).filter_by(id=ticket_id).one_or_none()
            if not ticket:
                raise ValueError(f"Тикет с id {ticket_id} не найден!")
            return ticket

    @classmethod
    async def edit_ticket_status(cls, ticket_id: int, new_status: str):
        """Редактирует статус тикета в БД по его ID"""
        with Session() as session:
            ticket = session.query(Ticket).filter_by(id=ticket_id).first()
            if ticket:
                ticket.status = new_status
                ticket.last_updated = datetime.utcnow()
                session.commit()

    @classmethod
    async def add_ticket(cls, ticket_dict: TicketDict):
        """Запись тикетов в БД"""
        with Session() as session:
            new_ticket = Ticket(
                user_uid=ticket_dict.user_uid,
                title=ticket_dict.title,
                description=ticket_dict.description,
                last_updated=datetime.utcnow(),
                status=ticket_dict.status
            )
            session.add(new_ticket)
            session.commit()
            return new_ticket.id


engine = create_engine("sqlite:///bot.db", echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(autoflush=False, bind=engine)
