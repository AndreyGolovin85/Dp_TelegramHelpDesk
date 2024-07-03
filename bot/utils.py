import aiogram
from aiogram.utils.formatting import as_list
from db import Ticket


def new_ticket(description, title, user_id):
    new = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "status": "new"}
    return new


def reply_list(item: dict | None = None) -> aiogram.utils.formatting.Text:
    if item is None:
        item = Ticket.list_tickets()[-1]
    return as_list(
        f"ID пользователя: {item['user_id']}",
        f"Заголовок: {item['title']}",
        f"Описание: {item['description']}",
        f"Статус: {item['status']}",
        sep='\n')


def get_index_ticket(ticket_dict: dict) -> int:
    ticket_index = Ticket.list_tickets().index(ticket_dict)
    return ticket_index


def get_ticket_dict(index_ticket: str) -> dict:
    ticket_dict = Ticket.list_tickets()[int(index_ticket)]
    return ticket_dict