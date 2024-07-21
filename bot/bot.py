import logging
from typing import Literal
import asyncio
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters.command import Command, CommandObject
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.utils.formatting import Text
from db import add_ticket, edit_ticket_status, get_ticket_by_id, list_tickets
from dotenv import load_dotenv
from utils import active_tickets, answer_register, check_user_registration, new_ticket, raw_reply, reply_list

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
_ADMIN_ID = os.getenv("ADMIN_ID")
if not API_TOKEN or not _ADMIN_ID:
    logging.error("Отстутствуют переменные ENV.")
    sys.exit(1)

bot = Bot(token=API_TOKEN)
ADMIN_ID = int(_ADMIN_ID)
dispatcher = Dispatcher()


def buttons_keyboard(
    ticket_id: int, keyboard_type: Literal["accept", "complete", "reject"] = "accept"
) -> types.InlineKeyboardMarkup:
    """
    Формирует клавиатуру в зависимости от нужного варианта.
    'accept' - по умолчанию, кнопки Принять / Отменить.
    'complete' - кнопки Отменить / Закрыть.
    """

    if keyboard_type == "accept":
        buttons = [
            [
                types.InlineKeyboardButton(
                    text="Принять заявку",
                    callback_data=f"ticket_accept_{ticket_id}",
                ),
                types.InlineKeyboardButton(
                    text="Отменить заявку",
                    callback_data=f"ticket_canceled_{ticket_id}",
                ),
            ],
        ]
    elif keyboard_type == "complete":
        buttons = [
            [
                types.InlineKeyboardButton(
                    text="Отменить заявку",
                    callback_data=f"ticket_canceled_{ticket_id}",
                ),
                types.InlineKeyboardButton(
                    text="Закрыть заявку",
                    callback_data=f"ticket_completed_{ticket_id}",
                ),
            ],
        ]
    else:
        buttons = [
            [
                types.InlineKeyboardButton(
                    text="Отменить заявку",
                    callback_data=f"ticket_usercancel_{ticket_id}",
                ),
            ],
        ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


@dispatcher.callback_query(lambda call: call.data.startswith("ticket_"))
async def send_message_users(callback: types.CallbackQuery):
    if not callback.data:
        return
    _, status, ticket_id = callback.data.split("_")
    if not (ticket := get_ticket_by_id(int(ticket_id))):
        return

    if status == "accept":
        edit_ticket_status(ticket.id, "in_work")
        await bot.send_message(
            chat_id=ticket.user_uid,
            text=f"Ваша заявка: {ticket.id} \nОписание: {ticket.description}\nпринята в работу!",
        )
        await callback.message.edit_text(
            f"Заявка {ticket_id} принята в работу. \nОписание заявки: {ticket.description}",
            reply_markup=buttons_keyboard(ticket_id, "complete"),
        )
    elif status == "canceled":
        edit_ticket_status(
            ticket.id,
            "rejected",
            "Заявка отменена администратором.",
        )
        await bot.send_message(
            chat_id=ticket.user_uid,
            text=f"Ваша заявка {ticket.id} отменена.",
        )
        await callback.message.edit_text(f"Заявка {ticket_id} отменена.")
    elif status == "usercancel":
        edit_ticket_status(
            ticket.id,
            "rejected",
            "Заявка отменена пользователем.",
        )
        await callback.message.edit_text(f"Вы отменили заявку {ticket.id}.")
        await bot.send_message(chat_id=ADMIN_ID, text=f"Заявка {ticket_id} отменена пользователем.")

    elif status == "completed":
        edit_ticket_status(ticket.id, "completed")
        await bot.send_message(
            chat_id=ticket.user_uid,
            text=f"Ваша заявка: {ticket.id} \nОписание: {ticket.description}\nвыполнена!",
        )
        await callback.message.edit_text(f"Заявка {ticket_id} завершена.")

    await callback.answer()


async def admin_to_accept_button(reply_text: Text, ticket_id: int):
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Новая заявка: \n{reply_text.as_html()}\nс номером {ticket_id} создана.",
        reply_markup=buttons_keyboard(ticket_id),
    )


@dispatcher.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Основные команды для работы:\n"
        "/register - команда для регистрации пользователя. При регистрации возможно указать свои имя/фамилию в формате"
        "\n<pre>/register Имя Фамилия\nВаш отдел</pre>\n"
        "/new_ticket - команда для создания новой заявки, <code>/new_ticket (опишите тут вашу проблему)</code>.\n"
        "/tickets - команда для проверки ваших заявок.\n"
        "/cancel - команда для отмены заявки <code>/cancel (номер тикета для отмены)</code>.\n"
        "/complete - команда для самостоятельного закрытия заявки "
        "<code>/complete (номер тикета для завершения)</code>.",
        parse_mode=ParseMode.HTML,
    )


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в бот!\nДля продолжения пройдите регистрацию /register или воспользуйтесь "
        "помощью по командам /help."
    )


@dispatcher.message(Command("register"))
async def cmd_register(message: types.Message, command: CommandObject) -> None:
    is_admin = False
    if message.chat.id == ADMIN_ID:
        is_admin = True
    if not command.args:
        await message.answer(
            "Правильное использование команды:\n"
            "<pre>/register Имя Фамилия\nВаш отдел (обязательно с новой строки!)</pre>"
            "\nВвод имени и фамилии не обязательны, если они указаны в вашем профиле Telegram, "
            "в таком случае команду писать так:\n"
            "<pre>/register Ваш отдел</pre>",
            parse_mode=ParseMode.HTML,
        )
        return
    if len(command.args.splitlines()) == 2:
        first_name, last_name = command.args.splitlines()[0].split()
        department = command.args.splitlines()[1]
    elif len(command.args.splitlines()) == 1:
        if not message.from_user.first_name and not message.from_user.last_name:
            await message.answer(
                "У вас не указано имя или фамилия в профиле телеграмма "
                "и вы не указали их в вводе. Пожалуйста, укажите имя и фамилию в команде.\n"
                "<pre>/register Имя Фамилия\nВаш отдел (обязательно с новой строки!)</pre>",
                parse_mode=ParseMode.HTML,
            )
            return
        first_name, last_name = message.from_user.first_name, message.from_user.last_name
        department = command.args
    else:
        return
    if not (ans := await answer_register(message, first_name, last_name, department, is_admin)):
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
        await message.reply(
            "Правильный вызов данной команды: */new_ticket <опишите тут вашу проблему>*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not check_user_registration(message.chat.id) or not message.from_user:
        await message.answer("Вы не зарегистрированы в боте, введите команду /register.")
        return
    ticket_dict = new_ticket(command.args, f"Запрос от {message.from_user.full_name}", message.chat.id)
    reply_text = raw_reply(ticket_dict)
    ticket_id = add_ticket(ticket_dict)
    await admin_to_accept_button(reply_text, ticket_id)
    if message.chat.id != ADMIN_ID:
        await message.reply(**reply_text.as_kwargs(), reply_markup=buttons_keyboard(ticket_id, "reject"))


@dispatcher.message(Command("cancel"))
async def cmd_cancel_ticket(message: types.Message, command: CommandObject) -> None:
    if command.args is None:
        await message.reply(
            "Правильный вызов данной команды: */cancel <номер тикета для отмены>*."
            "\nПод отменой подразумевается, что ваша проблема решаться не будет (например, тикет создан по ошибке).",
            parse_mode=ParseMode.MARKDOWN,
        )
        tickets = active_tickets(message.chat.id)
        await message.answer(tickets)
        return
    ticket_id = int(command.args)
    if not get_ticket_by_id(ticket_id):
        await message.reply("Вы не создавали тикета с таким номером.")
        return
    edit_ticket_status(ticket_id, "rejected", "Заявка отменена пользователем.")
    await message.reply(f"Ваш тикет под номером {ticket_id} успешно отменен.")
    await bot.send_message(chat_id=ADMIN_ID, text=f"Заявка {ticket_id} отменена пользователем.")


@dispatcher.message(Command("complete"))
async def cmd_complete_ticket(message: types.Message, command: CommandObject) -> None:
    if command.args is None:
        await message.reply(
            "Правильный вызов данной команды: */complete <номер тикета для завершения>*"
            "\nИспользовать, если проблема решена.",
            parse_mode=ParseMode.MARKDOWN,
        )
        tickets = active_tickets(message.chat.id)
        await message.answer(tickets)
        return
    ticket_id = int(command.args)
    if not get_ticket_by_id(ticket_id):
        await message.reply("Вы не создавали тикета с таким номером.")
        return
    edit_ticket_status(ticket_id, "completed", "Заявка завершена пользователем.")
    await message.reply(f"Ваш тикет под номером {ticket_id} успешно завершен.")
    await bot.send_message(chat_id=ADMIN_ID, text=f"Заявка {ticket_id} завершена пользователем.")


@dispatcher.message(Command("check_admin"))
async def cmd_check_authority(message: types.Message) -> None:
    if message.chat.id != ADMIN_ID:
        await message.reply("Нет прав администратора.")
        return

    await message.reply("Права администратора подтверждены.")
    # Регистрация администратора в таблице Users если он не записан в базе.
    if check_user_registration(message.chat.id) or not message.chat.first_name or not message.chat.last_name:
        return
    await answer_register(message, message.chat.first_name, message.chat.last_name, "Admin", True)


async def set_commands():
    commands = [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="register", description="Команда для регистрации пользователя"),
        BotCommand(command="new_ticket", description="Команда для создания новой заявки"),
        BotCommand(command="tickets", description="Команда для проверки ваших заявок"),
        BotCommand(command="cancel", description="Команда для отмены заявки"),
        BotCommand(command="complete", description="Команда для самостоятельного закрытия заявки"),
        BotCommand(command="help", description="Справка по командам"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def main():
    await set_commands()
    await dispatcher.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] - %(filename)s:%(lineno)d #%(levelname)-s - %(name)s - %(message)s",
        filename="bot.log",
        filemode="w",
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка сервера!")
