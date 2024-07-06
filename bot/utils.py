import aiogram
from aiogram.utils.formatting import as_list

from custom_types import UserDict
from db import Ticket, User


def answer_start(message):
    user_uid = message.chat.id
    first_name = message.chat.first_name
    last_name = message.chat.last_name
    user_dict = new_user(user_uid, first_name, last_name)
    user = check_user_registration(user_uid)
    if not user:
        User.add_user(user_dict)
        answer = "Вы успешно зарегистрировались!"
    else:
        answer = "Вы уже зарегистрированы!"
    return f"{first_name}, добро пожаловать в бот! {answer}"


def check_user_registration(user_uid):
    user = User.get_user_by_uid(user_uid)
    return user


def new_ticket(description, title, user_id):
    new = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "status": "new"}
    return new


def new_user(user_uid, first_name, last_name) -> UserDict:
    new = {
        "user_uid": user_uid,
        "first_name": first_name,
        "last_name": last_name}
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
