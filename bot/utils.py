import aiogram
from aiogram.utils.formatting import as_list

from custom_types import UserDict, TicketDict
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


def new_ticket(description: str, title: str, user_id: int) -> TicketDict:
    new = TicketDict(user_uid=user_id, title=title, description=description)
    return new


def new_user(user_uid: int, first_name: str, last_name: str) -> UserDict:
    user = UserDict(user_uid, first_name, last_name)
    return user


def reply_list(item: TicketDict | None = None) -> aiogram.utils.formatting.Text:
    if item is None:
        item = Ticket.list_tickets()[-1]
    return as_list(
        f"ID пользователя: {item.user_uid}",
        f"Заголовок: {item.title}",
        f"Описание: {item.description}",
        f"Статус: {item.status}",
        sep='\n')
