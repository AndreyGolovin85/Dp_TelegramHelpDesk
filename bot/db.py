from sqlalchemy import Integer, String, Text, create_engine, select, and_
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.orm import Mapped, mapped_column


class Base(DeclarativeBase):
    pass


engine = create_engine("sqlite:///bot.db", echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(autoflush=False, bind=engine)


class Ticket(Base, sessionmaker):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String['new', 'in_work', 'completed', 'rejected'])

    def __repr__(self) -> str:
        return f"User(user_id={self.uid} title={self.title!r}, description={self.description!r}, status = {self.status})"

    # Возвращает список словарей тикетов
    @classmethod
    def list_tickets(cls, uid=0, status: str | None = None) -> list[dict]:
        tickets_dict = []
        with Session() as session:
            if uid != 0:
                select_tickets = select(Ticket).where(uid == Ticket.uid)
            elif status is None:
                select_tickets = select(Ticket)
            else:
                select_tickets = select(Ticket).where(status == Ticket.status)

            for ticket in session.query(select_tickets.subquery()).all():
                tickets_dict.append({
                    "user_id": ticket.uid,
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
                    Ticket.uid == ticket_dict["user_id"],
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
                uid=ticket_dict["user_id"],
                title=ticket_dict["title"],
                description=ticket_dict["description"],
                status=ticket_dict["status"]
            )
            session.add(new_ticket)
            session.commit()
