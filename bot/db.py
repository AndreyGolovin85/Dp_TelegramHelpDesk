from sqlalchemy import Integer, String, Text, create_engine, select, and_, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from sqlalchemy.orm import Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_uid = mapped_column(Integer)
    first_name: Mapped[str] = mapped_column(String(30))
    last_name: Mapped[str] = mapped_column(String(30))
    department: Mapped[str] = mapped_column(String(50), default='')
    is_priority: Mapped[int] = mapped_column(Integer, default=0)

    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="user")

    def __repr__(self) -> str:
        return f"User=(id={self.id!s}, first_name={self.first_name!s}, last_name={self.last_name!s}," \
               f"department={self.department!s}, is_priority={self.is_priority!s})"

    @classmethod
    async def add_user(cls, user_dict: dict):
        with Session() as session:
            new_user = User(
                user_uid=user_dict["user_uid"],
                first_name=user_dict["first_name"],
                last_name=user_dict["last_name"]
            )
            session.add(new_user)
            session.commit()
            return new_user


class Ticket(Base, sessionmaker):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String['new', 'in_work', 'completed', 'rejected'])

    user_uid: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_uid"))
    user: Mapped["User"] = relationship("User", back_populates="tickets")

    def __repr__(self) -> str:
        return f"User(user_id={self.user_uid} title={self.title!r}, description={self.description!r}, status = {self.status})"

    # Возвращает список словарей тикетов
    @classmethod
    def list_tickets(cls, uid=0, status: str | None = None) -> list[dict]:
        tickets_dict = []
        with Session() as session:
            if uid != 0:
                select_tickets = select(Ticket).where(uid == Ticket.user_uid)
            elif status is None:
                select_tickets = select(Ticket)
            else:
                select_tickets = select(Ticket).where(status == Ticket.status)

            for ticket in session.query(select_tickets.subquery()).all():
                tickets_dict.append({
                    "user_id": ticket.user_uid,
                    "title": ticket.title,
                    "description": ticket.description,
                    "status": ticket.status})
        return tickets_dict

    # Редактирует статус тикетов в БД
    @classmethod
    async def edit_ticket_status(cls, ticket_dict: dict, new_status: str):
        with Session() as session:
            list_ticket = select(Ticket).where(
                and_(
                    Ticket.user_uid == ticket_dict["user_id"],
                    Ticket.title == ticket_dict["title"],
                    Ticket.description == ticket_dict["description"],
                    Ticket.status == ticket_dict["status"]))
            ticket = session.scalars(list_ticket).first()
            ticket.status = new_status
            session.commit()

    # Запись тикетов в БД
    @classmethod
    async def add_ticket(cls, ticket_dict: dict):
        with Session() as session:
            new_ticket = Ticket(
                user_uid=ticket_dict["user_id"],
                title=ticket_dict["title"],
                description=ticket_dict["description"],
                status=ticket_dict["status"]
            )
            session.add(new_ticket)
            session.flush()
            session.commit()
            return new_ticket


engine = create_engine("sqlite:///bot.db", echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(autoflush=False, bind=engine)
