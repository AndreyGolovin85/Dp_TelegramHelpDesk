import asyncio
import os
import logging

from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandObject
from aiogram.utils.formatting import as_list

logging.basicConfig(level=logging.INFO)

load_dotenv()

bot = Bot(token=os.getenv("API_TOKEN"))
admin_id = int(os.getenv("ADMIN_ID"))
dispatcher = Dispatcher()

tickets = [{"user_id": 0, "title": "Тестовое название", "description": "Тестовое описание", "status": "test"}]


def reply_list(item=None):
    """<class 'aiogram.utils.formatting.Text'>"""
    if item is None:
        item = tickets[-1]
    return as_list(
        f"User ID: {item['user_id']}",
        f"Title: {item['title']}",
        f"Description: {item['description']}",
        f"Status: {item['status']}",
        sep='\n')


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello!")


@dispatcher.message(Command("tickets"))
async def cmd_tickets(message: types.Message, command: CommandObject):
    if message.chat.id != admin_id:
        if command.args is not None:
            await message.answer("! Do not insert arguments here !")
        for item in tickets:
            if message.chat.id == item['user_id']:
                reply_text = reply_list(item)
                await message.answer(**reply_text.as_kwargs())
        return

    if command.args == "new":
        for item in tickets:
            if item['status'] == "new":
                reply_text = reply_list(item)
                await message.answer(**reply_text.as_kwargs())
        return

    if command.args is None:
        for item in tickets:
            reply_text = reply_list(item)
            await message.answer(**reply_text.as_kwargs())
        return


@dispatcher.callback_query(lambda call: call.data.startswith("accept_ticket:"))
async def send_message_users(callback: types.CallbackQuery):
    index_ticket = callback.data.split(":")[1]
    ticket = tickets[int(index_ticket)]
    ticket.update([("status", "in_work")])
    await bot.send_message(chat_id=ticket["user_id"], text=f"Ваша заявка: \n{reply_list(ticket).as_html()}"
                                                           f"\nпринята в работу.")
    await callback.message.answer("Заявка принята.")
    await callback.answer()


async def admin_to_accept_button(reply_text, ticket):
    id_ = tickets.index(ticket)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Принять заявку",
        callback_data=f"accept_ticket:{id_}"))
    await bot.send_message(chat_id=admin_id, text=f"Новая заявка: \n{reply_text.as_html()}",
                           reply_markup=builder.as_markup())


@dispatcher.message(Command("new_ticket"))
async def cmd_add_ticket(message: types.Message, command: CommandObject):
    if command.args is None:
        await message.reply("Proper usage of this command: */new_ticket <your issue here>*",
                            parse_mode=ParseMode.MARKDOWN)
        return

    ticket = {
        "user_id": message.chat.id,
        "title": f"{message.from_user.full_name}'s issue",
        "description": command.args,
        "status": "new"}
    tickets.append(ticket)
    reply_text = reply_list(ticket)
    await admin_to_accept_button(reply_text, ticket)
    await message.reply(**reply_text.as_kwargs())


@dispatcher.message(Command("check_admin"))
async def cmd_check_authority(message: types.Message):
    if message.chat.id == admin_id:
        await message.reply("Admin authority confirmed.")
        return

    await message.reply("Missing admin privileges.")


async def main():
    await dispatcher.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка сервера!")
