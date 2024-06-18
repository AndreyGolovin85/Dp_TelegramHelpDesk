import asyncio
import os
import logging

from aiogram.enums import ParseMode
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandObject
from aiogram.utils.formatting import as_list

logging.basicConfig(level=logging.INFO)

load_dotenv()

bot = Bot(token=os.getenv("API_TOKEN"))
admin_id = int(os.getenv("ADMIN_ID"))
dispatcher = Dispatcher()

tickets = [{"user_id": 0, "title": "Тестовое название", "description": "Тестовое описание", "status": "test"}]


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello!")


def reply_list(item):
    if not item:
        item = tickets[-1]
    return as_list(
        f"User ID: {item['user_id']}",
        f"Title: {item['title']}",
        f"Description: {item['description']}",
        f"Status: {item['status']}",
        sep='\n')


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
    await message.reply(**reply_text.as_kwargs())


@dispatcher.message(Command("check_admin"))
async def cmd_check_authority(message: types.Message):
    if message.chat.id == admin_id:
        await message.reply("Admin authority confirmed.")
        return

    await message.reply("Missing admin privileges.")


async def main():
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
