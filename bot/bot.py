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
dispatcher = Dispatcher()

tickets = [{"user_id": "id_tg_user", "title": "Название", "description": "описание", "status": "new"}]


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello!")


@dispatcher.message(Command("tickets"))
async def cmd_tickets(message: types.Message):
    for item in tickets:
        reply = as_list(
            f"User ID: {item['user_id']}",
            f"Title: {item['title']}",
            f"Description: {item['description']}",
            f"Status: {item['status']}",
            sep='\n'
        )
        await message.answer(**reply.as_kwargs())


@dispatcher.message(Command("new_ticket"))
async def cmd_tickets(message: types.Message, command: CommandObject):
    if command.args is None:
        await message.reply("Proper usage of this command: */new_ticket <your issue here>*",
                            parse_mode=ParseMode.MARKDOWN)
    else:
        print(command.args)
        tickets.append(
            {"user_id": str(message.chat.id), "title": f"{message.from_user.full_name}'s issue", "description": command.args,
             "status": "new"})
        reply = as_list(
            f"User ID: {tickets[-1]['user_id']}",
            f"Title: {tickets[-1]['title']}",
            f"Description: {tickets[-1]['description']}",
            f"Status: {tickets[-1]['status']}",
            sep='\n')
        await message.reply(**reply.as_kwargs())


async def main():
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
