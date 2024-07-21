import logging
from typing import Literal
import asyncio
import os
import sys

from aiogram import Bot, Dispatcher, filters, types
from aiogram.enums import ParseMode
from aiogram.filters.command import Command, CommandObject
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.formatting import Text
from db import (
    add_blocked_user,
    add_ticket,
    all_blocked_users,
    check_blocked,
    edit_ticket_status,
    get_ticket_by_id,
    list_tickets,
    unblock_user,
)
from dotenv import load_dotenv
from utils import active_tickets, answer_register, check_user_registration, new_ticket, raw_reply, reply_list

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
_ADMIN_ID = os.getenv("ADMIN_ID")
ACCESS_KEY = os.getenv("ACCESS_KEY")
if not API_TOKEN or not _ADMIN_ID or not ACCESS_KEY:
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


async def generate_start_link(our_bot: Bot):
    return await create_start_link(our_bot, ACCESS_KEY)


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
    if check_blocked(message.from_user.id) is True:
        return
    await message.answer(
        "Основные команды для работы:\n"
        "/register - команда для регистрации пользователя. При регистрации возможно указать свои имя/фамилию в формате"
        "<code>/register Имя Фамилия</code>\n"
        "/new_ticket - команда для создания новой заявки, <code>/new_ticket (опишите тут вашу проблему)</code>.\n"
        "/tickets - команда для проверки ваших заявок.\n"
        "/cancel - команда для отмены заявки <code>/cancel (номер тикета для отмены)</code>.\n"
        "/complete - команда для самостоятельного закрытия заявки "
        "<code>/complete (номер тикета для завершения)</code>.",
        parse_mode=ParseMode.HTML,
    )


till_block_counter = {}


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    if check_blocked(message.from_user.id) is True:
        return
    if command.args == ACCESS_KEY:
        await message.answer(
            "Добро пожаловать в бот!\nДля продолжения пройдите регистрацию /register или воспользуйтесь "
            "помощью по командам /help."
        )
        return
    if message.chat.id not in till_block_counter:
        till_block_counter[message.from_user.id] = 5
    if till_block_counter[message.from_user.id] > 0:
        await message.answer(
            f"Вы не предоставили ключ доступа к боту. "
            f"У вас осталось {till_block_counter[message.from_user.id]} попыток до блокировки."
        )
        till_block_counter[message.from_user.id] -= 1
    else:
        add_blocked_user(message.from_user.id, message.from_user.username)
        await message.answer("Вы были заблокированы. Обратитесь к администратору бота для разблокировки.")
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Пользователь {message.from_user.id} был заблокирован за 5 попыток запуска без ключа.",
        )


@dispatcher.my_chat_member(filters.ChatMemberUpdatedFilter(member_status_changed=filters.JOIN_TRANSITION))
async def my_chat_member(message: types.Message) -> None:
    await message.answer("Я не работаю в группах.")
    await bot.leave_chat(message.chat.id)


@dispatcher.message(Command("register"))
async def cmd_register(message: types.Message, command: CommandObject) -> None:
    if check_blocked(message.from_user.id) is True:
        return
    is_admin = False
    if message.chat.id == ADMIN_ID:
        is_admin = True
    if command.args is None:
        if message.chat.first_name and message.chat.last_name:
            first_name, last_name = message.chat.first_name, message.chat.last_name
        else:
            await message.answer(
                "У вас не указано имя или фамилия в профиле телеграмма "
                "и вы не указали их в вводе. Пожалуйста, укажите имя и фамилию в команде.\n"
                "<code>/register Имя Фамилия</code>",
                parse_mode=ParseMode.HTML,
            )
            return
    else:
        first_name, last_name = command.args.split()
    if not (ans := await answer_register(message, first_name, last_name, is_admin)):
        return
    await message.answer(ans)


@dispatcher.message(Command("tickets"))
async def cmd_tickets(message: types.Message, command: CommandObject) -> None:
    if check_blocked(message.from_user.id) is True:
        return
    if not check_user_registration(message.chat.id):
        await message.answer("Вы не зарегистрированы.")
        return

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
    if check_blocked(message.from_user.id) is True:
        return
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
    if check_blocked(message.from_user.id) is True:
        return
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
    if check_blocked(message.from_user.id) is True:
        return
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
    if check_blocked(message.from_user.id) is True:
        return
    if message.chat.id != ADMIN_ID:
        await message.reply("Нет прав администратора.")
        return

    await message.reply("Права администратора подтверждены.")
    # Регистрация администратора в таблице Users если он не записан в базе.
    if check_user_registration(message.chat.id) or not message.chat.first_name or not message.chat.last_name:
        return
    await answer_register(message, message.chat.first_name, message.chat.last_name, is_admin=True)


@dispatcher.message(Command("block"))
async def cmd_block_user(message: types.Message, command: CommandObject) -> None:
    if message.chat.id != ADMIN_ID:
        return
    if command.args is None:
        await message.reply("Укажите UID пользователя для блокировки.")
    add_blocked_user(int(command.args), "Added by admin.")
    await bot.send_message(chat_id=int(command.args), text="Вы были заблокированы администратором бота.")
    if check_blocked(int(command.args)):
        await message.answer(f"Пользователь {int(command.args)} заблокирован.")


@dispatcher.message(Command("unblock"))
async def cmd_unblock_user(message: types.Message, command: CommandObject) -> None:
    if message.chat.id != ADMIN_ID:
        return
    if command.args is None:
        await message.reply("Укажите UID пользователя для разблокировки.")
        if blocklist := all_blocked_users():
            await message.answer("\n".join(blocklist))
        else:
            await message.answer("На данный момент нет заблокированных пользователей.")
    unblock_user(int(command.args))
    till_block_counter.pop(int(command.args))
    await bot.send_message(chat_id=int(command.args), text="Вы были разблокированы администратором бота.")
    if not check_blocked(int(command.args)):
        await message.answer(f"Пользователь {int(command.args)} разблокирован.")


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
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Бот запущен, приглашение работает по ссылке {await generate_start_link(bot)}",
    )
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
