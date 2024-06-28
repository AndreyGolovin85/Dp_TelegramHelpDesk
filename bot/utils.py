import aiogram
from aiogram.utils.formatting import as_list
from db import list_tickets


def new_ticket(description, title, user_id):
    new = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "status": "new"}
    return new


def reply_list(item: dict | None = None) -> aiogram.utils.formatting.Text:
    if item is None:
        item = list_tickets()[-1]
    return as_list(
        f"User ID: {item['user_id']}",
        f"Title: {item['title']}",
        f"Description: {item['description']}",
        f"Status: {item['status']}",
        sep='\n')


def get_index_ticket(ticket_dict: dict) -> int:
    ticket_index = list_tickets().index(ticket_dict)
    return ticket_index


def get_ticket_dict(index_ticket: str) -> dict:
    ticket_dict = list_tickets()[int(index_ticket)]
    return ticket_dict
