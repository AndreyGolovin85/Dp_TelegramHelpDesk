import asyncio
import os
import logging

from aiogram.enums import ParseMode
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandObject

from db import Ticket
from utils import reply_list, new_ticket, answer_start, check_user_registration

load_dotenv()
bot = Bot(token=os.getenv("API_TOKEN"))
admin_id = int(os.getenv("ADMIN_ID"))
dispatcher = Dispatcher()


def buttons_keyboard(ticket_id: int, keyboard_type: int = 0):
    if keyboard_type == 0:
        buttons = [
            [
                types.InlineKeyboardButton(text="Принять заявку", callback_data=f"ticket_accept_{ticket_id}"),
                types.InlineKeyboardButton(text="Отменить заявку", callback_data=f"ticket_canceled_{ticket_id}"),
            ]
        ]
    elif keyboard_type == 1:
        buttons = [
            types.InlineKeyboardButton(text="Отменить заявку", callback_data=f"ticket_canceled_{ticket_id}"),
            types.InlineKeyboardButton(text="Закрыть заявку", callback_data=f"ticket_completed_{ticket_id}")
        ]
    else:  # Как заготовка, на случай если захочется повозиться и добавить кнопку отмены под каждый тикет в выводе
        buttons = [types.InlineKeyboardButton(text="Отменить заявку", callback_data=f"ticket_canceled_{ticket_id}")]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


@dispatcher.callback_query(lambda call: call.data.startswith("ticket_"))
async def send_message_users(callback: types.CallbackQuery):
    status = callback.data.split("_")[1]
    ticket_id = callback.data.split("_")[2]
    ticket = Ticket.get_ticket_by_id(int(ticket_id))
    if status == "accept":
        await Ticket.edit_ticket_status(ticket.id, "in_work")
        await bot.send_message(chat_id=ticket.user_uid,
                               text=f"Ваша заявка: {ticket.id} \nОписание: {ticket.description}\nпринята в работу!")
        await admin_complete_button(ticket_id)
    elif status == "canceled":
        await Ticket.edit_ticket_status(ticket.id, "rejected", "Заявка отменена администратором.")
        await bot.send_message(chat_id=ticket.user_uid,
                               text=f"Ваша заявка {ticket.id} отменена.")
    elif status == "completed":
        await Ticket.edit_ticket_status(ticket.id, status)
        await bot.send_message(chat_id=ticket.user_uid,
                               text=f"Ваша заявка: {ticket.id} \nОписание: {ticket.description}\nвыполнена!")

    await callback.answer()


async def admin_complete_button(ticket_id):
    await bot.send_message(chat_id=admin_id, text=f"Заявка {ticket_id} принята в работу!",
                           reply_markup=buttons_keyboard(ticket_id, 1))


async def admin_to_accept_button(reply_text, ticket_id):
    await bot.send_message(chat_id=admin_id, text=f"Новая заявка: \n{reply_text.as_html()}\n"
                                                  f"с номером {ticket_id} создана.",
                           reply_markup=buttons_keyboard(ticket_id))


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(answer_start(message))


@dispatcher.message(Command("tickets"))
async def cmd_tickets(message: types.Message, command: CommandObject):
    if message.chat.id != admin_id:
        if command.args is not None:
            await message.answer("! Не пишите лишние аргументы !")
        user_tickets = Ticket.list_tickets(uid=message.chat.id)
        if not user_tickets:
            await message.answer("Вы ещё не создали ни одного тикета.")
        for user_ticket in user_tickets:
            await message.answer(**reply_list(user_ticket).as_kwargs())
        return

    if command.args == "new":
        user_tickets = Ticket.list_tickets(status="new")
        for user_ticket in user_tickets:
            await message.answer(**reply_list(user_ticket).as_kwargs())
        return

    if command.args is None:
        user_tickets = Ticket.list_tickets()
        for user_ticket in user_tickets:
            await message.answer(**reply_list(user_ticket).as_kwargs())
        return


@dispatcher.message(Command("new_ticket"))
async def cmd_add_ticket(message: types.Message, command: CommandObject):
    if command.args is None:
        await message.reply("Правильный вызов данной команды: */new_ticket <опишите тут вашу проблему>*",
                            parse_mode=ParseMode.MARKDOWN)
        return

    user = check_user_registration(message.chat.id)
    if not user:
        await message.answer("Вы не зарегистрированы в боте, введите команду /start.")
    else:
        ticket_dict = new_ticket(command.args, f"Запрос от {message.from_user.full_name}", message.chat.id)
        reply_text = reply_list(ticket_dict)
        ticket_id = await Ticket.add_ticket(ticket_dict)
        await admin_to_accept_button(reply_text, ticket_id)
        if message.chat.id != admin_id:
            await message.reply(**reply_text.as_kwargs())


@dispatcher.message(Command("cancel"))
async def cmd_cancel_ticket(message: types.Message, command: CommandObject):
    if command.args is None:
        await message.reply("Правильный вызов данной команды: */cancel <номер тикета для отмены>*",
                            parse_mode=ParseMode.MARKDOWN)
        tickets = Ticket.list_ticket_ids(message.chat.id)
        string_ticket = "Список ваших активных тикетов:"
        inactive = 0
        for ticket in tickets:
            if ticket["status"] not in ["completed", "rejected"]:
                tmp = f"\n" + str(ticket["id"]) + ": " + ticket["description"] + ". Статус: " + ticket["status"]
                string_ticket += tmp
            else:
                inactive += 1
        if not tickets or inactive == len(tickets):
            await message.answer("У вас нет активных тикетов.")
        await message.answer(string_ticket)
        return
    if not Ticket.list_tickets(uid=message.chat.id):
        await message.answer("Вы ещё не создали ни одного тикета.")
        return
    ticket_id = int(command.args)
    if not Ticket.get_ticket_by_id(ticket_id):
        await message.reply("Вы не создавали тикета с таким номером.")
        return
    await Ticket.edit_ticket_status(ticket_id, "rejected", "Заявка отменена пользователем.")
    await message.reply(f"Ваш тикет под номером {ticket_id} успешно отменен.")


@dispatcher.message(Command("check_admin"))
async def cmd_check_authority(message: types.Message):
    if message.chat.id == admin_id:
        await message.reply("Права администратора подтверждены.")
        return

    await message.reply("Нет прав администратора.")


async def main():
    await dispatcher.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка сервера!")
