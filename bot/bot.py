import asyncio
import os
import logging

from aiogram.enums import ParseMode
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandObject

from utils import tickets_write, reply_list, cmd_tickets_new, cmd_tickets_none, cmd_tickets_not_admin

logging.basicConfig(level=logging.INFO)

load_dotenv()

bot = Bot(token=os.getenv("API_TOKEN"))
admin_id = int(os.getenv("ADMIN_ID"))
dispatcher = Dispatcher()


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello!")


@dispatcher.message(Command("tickets"))
async def cmd_tickets(message: types.Message, command: CommandObject):
    command_args = command.args
    user_id = message.chat.id
    if user_id != admin_id:
        if command_args is not None:
            await message.answer("! Do not insert arguments here !")
        reply_text = cmd_tickets_not_admin(user_id)
        await message.answer(**reply_text.as_kwargs())
        return

    if command_args == "new":
        reply_text = cmd_tickets_new(command_args)
        await message.answer(**reply_text.as_kwargs())
        return

    if command_args is None:
        reply_text = cmd_tickets_none()
        await message.answer(**reply_text.as_kwargs())
        return


@dispatcher.message(Command("new_ticket"))
async def cmd_add_ticket(message: types.Message, command: CommandObject):
    if command.args is None:
        await message.reply("Proper usage of this command: */new_ticket <your issue here>*",
                            parse_mode=ParseMode.MARKDOWN)
        return

    user_id = message.chat.id
    title = f"{message.from_user.full_name}'s issue"
    description = command.args

    ticket = tickets_write(description, title, user_id)
    reply_text = reply_list(ticket)
    await message.reply(**reply_text.as_kwargs())
    await bot.send_message(chat_id=admin_id, text=f"Новая заявка: \n{reply_text.as_html()}")


@dispatcher.message(Command("check_admin"))
async def cmd_check_authority(message: types.Message):
    if message.chat.id == admin_id:
        await message.reply("Admin authority confirmed.")
        return

    await message.reply("Missing admin privileges.")


async def main():
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка сервера!")
