from datetime import datetime, timezone
from collections.abc import Sequence
from sqlalchemy import select

from custom_types import UserDTO, TicketDictID, status_type, TicketDict
from models import User, Session, Ticket, BlockedUser


# Функции обработки пользователя.
def get_user_by_uid(user_uid: int) -> User | None:
    with Session() as session:
        return session.query(User).filter_by(user_uid=user_uid).one_or_none()


def add_user(user_dict: UserDTO) -> User:
    with Session() as session:
        new_user = User(
            user_uid=user_dict.user_uid,
            first_name=user_dict.first_name,
            last_name=user_dict.last_name,
            department=user_dict.department,
            is_priority=user_dict.is_priority,
        )
        session.add(new_user)
        session.commit()
        return new_user


# Функции обработки тикетов.
def list_tickets(uid=0, status: str | None = None) -> Sequence[TicketDict]:
    """Возвращает список словарей тикетов"""
    with Session() as session:
        if uid != 0:
            select_tickets = select(Ticket).where(Ticket.user_uid.__eq__(uid))
        elif status is None:
            select_tickets = select(Ticket)
        else:
            select_tickets = select(Ticket).where(Ticket.status.__eq__(status))

        return [
            TicketDict.model_validate(ticket, from_attributes=True)
            for ticket in session.query(select_tickets.subquery()).all()
        ]


def list_ticket_ids(uid: int) -> Sequence[TicketDictID]:
    """Получает список словарей с ID тикетов"""
    with Session() as session:
        select_tickets = select(Ticket).where(Ticket.user_uid.__eq__(uid))
        return [
            TicketDictID.model_validate(ticket, from_attributes=True)
            for ticket in session.query(select_tickets.subquery()).all()
        ]


def get_ticket_by_id(ticket_id: int) -> Ticket | None:
    """Получает тикет из базы данных по его id."""
    with Session() as session:
        ticket: Ticket | None = session.query(Ticket).filter_by(id=ticket_id).one_or_none()
        if not ticket:
            print(f"Тикет с id {ticket_id} не найден!")
            return
        return ticket


def edit_ticket_status(
        ticket_id: int, new_status: status_type, reason: str = "Тикет завершен администратором.") -> None:
    """Редактирует статус тикета в БД по его ID"""
    with Session() as session:
        ticket = session.query(Ticket).filter_by(id=ticket_id).one_or_none()
        if ticket:
            if new_status in ("rejected", "completed"):
                ticket.update_reason = reason
            ticket.status = new_status
            ticket.last_updated = datetime.now(tz=timezone.utc)
            session.commit()


def add_ticket(ticket_dict: TicketDict) -> int:
    """Запись тикетов в БД"""
    with Session() as session:
        new_ticket = Ticket(
            user_uid=ticket_dict.user_uid,
            title=ticket_dict.title,
            description=ticket_dict.description,
            dates_created=datetime.now(tz=timezone.utc),
            last_updated=datetime.now(tz=timezone.utc),
            status=ticket_dict.status,
        )
        session.add(new_ticket)
        session.commit()
        return new_ticket.id


# Функции обработки заблокированных пользователей.
def add_blocked_user(user_uid: int, user_name: str):
    with Session() as session:
        blocked_user = session.query(BlockedUser).filter_by(user_uid=user_uid).one_or_none()
        if not blocked_user:
            blocked_user = BlockedUser(user_uid=user_uid, username=user_name, is_blocked=True)
            session.add(blocked_user)
        else:
            blocked_user.is_blocked = True

        session.commit()


def unblock_user(user_uid: int):
    with Session() as session:
        blocked_user = session.query(BlockedUser).filter_by(user_uid=user_uid).one_or_none()
        if blocked_user:
            if blocked_user.is_blocked:
                blocked_user.is_blocked = False
                session.commit()


def check_blocked(user_uid: int) -> bool:
    with Session() as session:
        blocked_user = session.query(BlockedUser).filter_by(user_uid=user_uid).one_or_none()
        if blocked_user:
            return blocked_user.is_blocked


def all_blocked_users():
    with Session() as session:
        return [[blocked_user.user_uid, blocked_user.username]
                for blocked_user in session.query(BlockedUser).filter(BlockedUser.is_blocked).all()]
