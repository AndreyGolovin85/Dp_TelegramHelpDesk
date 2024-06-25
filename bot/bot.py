import asyncio
import os
import logging

from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandObject


from utils import reply_list, cmd_tickets_new, cmd_tickets_none, cmd_tickets_not_admin, ticket, get_index_ticket, \
    get_ticket_dict

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
    ticket_dict.update([("status", "in_work")])
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

    ticket_dict = ticket(message, command)
    reply_text = reply_list(ticket_dict)
    await admin_to_accept_button(reply_text, ticket_dict)
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
