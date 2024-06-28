import asyncio
import os
import logging

from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandObject

from db import add_ticket, edit_ticket_status, list_tickets
from utils import reply_list, new_ticket, get_index_ticket, get_ticket_dict

logging.basicConfig(level=logging.INFO)

load_dotenv()
bot = Bot(token=os.getenv("API_TOKEN"))
admin_id = int(os.getenv("ADMIN_ID"))
dispatcher = Dispatcher()


def get_keyboard(text, call_data):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text=text, callback_data=call_data))
    return builder.as_markup()


@dispatcher.callback_query(lambda call: call.data.startswith("accept_ticket:"))
async def send_message_users(callback: types.CallbackQuery):
    index_ticket = callback.data.split(":")[1]
    ticket_dict = get_ticket_dict(index_ticket)
    await edit_ticket_status(ticket_dict, "in_work")
    await bot.send_message(chat_id=ticket_dict["user_id"],
                           text=f"Ваша заявка: \n{reply_list(ticket_dict).as_html()}\nпринята в работу!")
    # Требуется переделать.
    await callback.message.answer("Заявка принята в работу!",
                                  reply_markup=get_keyboard("Закрыть заявку", f"accept_ticket:{index_ticket}"))
    await callback.answer()


async def admin_to_accept_button(reply_text, ticket_dict):
    index_ticket = get_index_ticket(ticket_dict)
    await bot.send_message(chat_id=admin_id, text=f"Новая заявка: \n{reply_text.as_html()}",
                           reply_markup=get_keyboard("Принять заявку", f"accept_ticket:{index_ticket}"))


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello!")


@dispatcher.message(Command("tickets"))
async def cmd_tickets(message: types.Message, command: CommandObject):
    user_id = message.chat.id
    if user_id != admin_id:
        if command.args is not None:
            await message.answer("! Не пишите лишние аргументы !")
        user_tickets = list_tickets(user_id)
        if user_tickets is None:
            await message.answer("Вы ещё не создали ни одного тикета.")
        for user_ticket in user_tickets:
            await message.answer(**reply_list(user_ticket).as_kwargs())
        return

    if command.args == "new":
        user_tickets = list_tickets(status="new")
        for user_ticket in user_tickets:
            await message.answer(**reply_list(user_ticket).as_kwargs())
        return

    if command.args is None:
        user_tickets = list_tickets()
        for user_ticket in user_tickets:
            await message.answer(**reply_list(user_ticket).as_kwargs())
        return


@dispatcher.message(Command("new_ticket"))
async def cmd_add_ticket(message: types.Message, command: CommandObject):
    if command.args is None:
        await message.reply("Правильный вызов данной команды: */new_ticket <опишите тут вашу проблему>*",
                            parse_mode=ParseMode.MARKDOWN)
        return

    ticket_dict = new_ticket(command.args, f"{message.from_user.full_name}'s issue", message.chat.id)
    reply_text = reply_list(ticket_dict)
    await add_ticket(ticket_dict)
    await admin_to_accept_button(reply_text, ticket_dict)
    await message.reply(**reply_text.as_kwargs())


@dispatcher.message(Command("check_admin"))
async def cmd_check_authority(message: types.Message):
    if message.chat.id == admin_id:
        await message.reply("Права администратора подтверждены.")
        return

    await message.reply("Нет прав администратора.")


async def main():
    await dispatcher.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка сервера!")
