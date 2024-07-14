import asyncio
import logging
import os
import sys
from typing import Literal

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters.command import Command, CommandObject
from custom_types import UserDict
from db import add_ticket, add_user, edit_ticket_status, get_ticket_by_id, list_tickets
from dotenv import load_dotenv
from utils import active_tickets, answer_start, check_user_registration, new_ticket, raw_reply, reply_list

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
_ADMIN_ID = os.getenv("ADMIN_ID")
if not API_TOKEN or not _ADMIN_ID:
    sys.exit(1)

bot = Bot(token=API_TOKEN)
ADMIN_ID = int(_ADMIN_ID)
dispatcher = Dispatcher()


def buttons_keyboard(ticket_id: int, keyboard_type: Literal["accept", "complete"] = "accept") -> types.InlineKeyboardMarkup:
    """ Формирует клавиатуру в зависимости от нужного варианта.
    'accept' - по умолчанию, кнопки Принять / Отменить.
    'complete' - кнопки Отменить / Закрыть """
    if keyboard_type == "accept":
        buttons = [
            [
                types.InlineKeyboardButton(text="Принять заявку", callback_data=f"ticket_accept_{ticket_id}"),
                types.InlineKeyboardButton(text="Отменить заявку", callback_data=f"ticket_canceled_{ticket_id}")
            ]
        ]
    elif keyboard_type == "complete":
        buttons = [
            [
                types.InlineKeyboardButton(text="Отменить заявку", callback_data=f"ticket_canceled_{ticket_id}"),
                types.InlineKeyboardButton(text="Закрыть заявку", callback_data=f"ticket_completed_{ticket_id}")
            ]
        ]
    else:  # Как заготовка, на случай если захочется повозиться и добавить кнопку отмены под каждый тикет в выводе
        buttons = [[types.InlineKeyboardButton(text="Отменить заявку", callback_data=f"ticket_canceled_{ticket_id}")]]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


@dispatcher.callback_query(lambda call: call.data.startswith("ticket_"))
async def send_message_users(callback: types.CallbackQuery):
    if not callback.data:
        return
    _, status, ticket_id = callback.data.split("_")
    if not (ticket := get_ticket_by_id(int(ticket_id))):
        return

    if status == "accept":
        await edit_ticket_status(ticket.id, "in_work")
        await bot.send_message(chat_id=ticket.user_uid,
                               text=f"Ваша заявка: {ticket.id} \nОписание: {ticket.description}\nпринята в работу!")
        await admin_complete_button(ticket_id)
    elif status == "canceled":
        await edit_ticket_status(ticket.id, "rejected", "Заявка отменена администратором.")
        await bot.send_message(chat_id=ticket.user_uid,
                               text=f"Ваша заявка {ticket.id} отменена.")
    elif status == "completed":
        await edit_ticket_status(ticket.id, "completed")
        await bot.send_message(chat_id=ticket.user_uid,
                               text=f"Ваша заявка: {ticket.id} \nОписание: {ticket.description}\nвыполнена!")

    await callback.answer()


async def admin_complete_button(ticket_id):
    await bot.send_message(chat_id=ADMIN_ID, text=f"Заявка {ticket_id} принята в работу!", reply_markup=buttons_keyboard(ticket_id, "complete"))


async def admin_to_accept_button(reply_text, ticket_id):
    await bot.send_message(chat_id=ADMIN_ID, text=f"Новая заявка: \n{reply_text.as_html()}\n" f"с номером {ticket_id} создана.", reply_markup=buttons_keyboard(ticket_id))


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    if not (ans := await answer_start(message)):
        return
    await message.answer(ans)


@dispatcher.message(Command("tickets"))
async def cmd_tickets(message: types.Message, command: CommandObject) -> None:
    if message.chat.id != ADMIN_ID:
        if command.args is not None:
            await message.answer("! Не пишите лишние аргументы !")
        if not (user_tickets := list_tickets(uid=message.chat.id)):
            await message.answer("Вы ещё не создали ни одного тикета.")
            return
        for user_ticket in user_tickets:
            await message.answer(**reply_list(user_ticket))
        return

    if command.args != "new":
        if not (user_tickets := list_tickets()):
            await message.reply("В базе данных нет тикетов.")
            return
        for user_ticket in user_tickets:
            await message.answer(**reply_list(user_ticket))
        return

    if not (user_tickets := list_tickets(status="new")):
        await message.reply("В базе данных нет тикетов.")
        return
    for user_ticket in user_tickets:
        await message.answer(**reply_list(user_ticket))


@dispatcher.message(Command("new_ticket"))
async def cmd_add_ticket(message: types.Message, command: CommandObject) -> None:
    if command.args is None:
        await message.reply("Правильный вызов данной команды: */new_ticket <опишите тут вашу проблему>*",
                            parse_mode=ParseMode.MARKDOWN)
        return

    if not check_user_registration(message.chat.id) or not message.from_user:
        await message.answer("Вы не зарегистрированы в боте, введите команду /start.")
        return
    ticket_dict = new_ticket(command.args, f"Запрос от {message.from_user.full_name}", message.chat.id)
    reply_text = raw_reply(ticket_dict)
    ticket_id = await add_ticket(ticket_dict)
    await admin_to_accept_button(reply_text, ticket_id)
    if message.chat.id != ADMIN_ID:
        await message.reply(**reply_text.as_kwargs())


@dispatcher.message(Command("cancel"))
async def cmd_cancel_ticket(message: types.Message, command: CommandObject) -> None:
    if command.args is None:
        await message.reply("Правильный вызов данной команды: */cancel <номер тикета для отмены>*."
                            "\nПод отменой подразумевается, что ваша проблема решаться не будет (например, тикет создан по ошибке).",
                            parse_mode=ParseMode.MARKDOWN)
        tickets = active_tickets(message.chat.id)
        await message.answer(tickets)
        return
    ticket_id = int(command.args)
    if not get_ticket_by_id(ticket_id):
        await message.reply("Вы не создавали тикета с таким номером.")
        return
    await edit_ticket_status(ticket_id, "rejected", "Заявка отменена пользователем.")
    await message.reply(f"Ваш тикет под номером {ticket_id} успешно отменен.")


@dispatcher.message(Command("complete"))
async def cmd_complete_ticket(message: types.Message, command: CommandObject) -> None:
    if command.args is None:
        await message.reply("Правильный вызов данной команды: */complete <номер тикета для завершения>*"
                            "\nИспользовать, если проблема решена.",
                            parse_mode=ParseMode.MARKDOWN)
        tickets = active_tickets(message.chat.id)
        await message.answer(tickets)
        return
    ticket_id = int(command.args)
    if not get_ticket_by_id(ticket_id):
        await message.reply("Вы не создавали тикета с таким номером.")
        return
    await edit_ticket_status(ticket_id, "completed", "Заявка завершена пользователем.")
    await message.reply(f"Ваш тикет под номером {ticket_id} успешно завершен.")


@dispatcher.message(Command("check_admin"))
async def cmd_check_authority(message: types.Message) -> None:
    if message.chat.id != ADMIN_ID:
        await message.reply("Нет прав администратора.")
        return

    await message.reply("Права администратора подтверждены.")
    # Регистрация администратора в таблице Users если он не записан в базе
    if check_user_registration(message.chat.id) or not message.chat.first_name or not message.chat.last_name:
        return
    user_dict = UserDict(user_uid=message.chat.id, first_name=message.chat.first_name, last_name=message.chat.last_name, department="Admin", is_priority=99)
    await add_user(user_dict)


async def main():
    await dispatcher.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка сервера!")
