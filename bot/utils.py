import aiogram
from aiogram.utils.formatting import as_list

tickets = [{"user_id": 0, "title": "Тестовое название", "description": "Тестовое описание", "status": "test"}]


def tickets_write(description, title, user_id):
    new_ticket = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "status": "new"}
    tickets.append(new_ticket)
    return new_ticket


def reply_list(item: dict = None) -> aiogram.utils.formatting.Text:
    if item is None:
        item = tickets[-1]
    return as_list(
        f"User ID: {item['user_id']}",
        f"Title: {item['title']}",
        f"Description: {item['description']}",
        f"Status: {item['status']}",
        sep='\n')


def ticket(message, command):
    user_id = message.chat.id
    title = f"{message.from_user.full_name}'s issue"
    description = command.args
    new_ticket = tickets_write(description, title, user_id)
    return new_ticket


def cmd_tickets_new(command_args):
    for item in tickets:
        if item["status"] == command_args:
            return reply_list(item)


def cmd_tickets_none():
    for item in tickets:
        return reply_list(item)


def cmd_tickets_not_admin(user_id):
    for item in tickets:
        if item['user_id'] == user_id:
            return reply_list(item)


def get_index_ticket(ticket_dict: dict) -> int:
    ticket_index = tickets.index(ticket_dict)
    return ticket_index


def get_ticket_dict(index_ticket: str) -> dict:
    ticket_dict = tickets[int(index_ticket)]
    return ticket_dict
