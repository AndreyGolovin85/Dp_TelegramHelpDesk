from typing import Literal
import asyncio

from aiogram import Bot, filters, types, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters.command import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.formatting import Text
from custom_types import RegisterStates, TicketStates, AdminChatState
from db_utils import add_blocked_user, add_ticket, all_blocked_users, check_blocked, edit_ticket_status,\
    get_ticket_by_id, list_tickets, unblock_user
from utils import active_tickets, answer_register, check_user_registration, new_ticket, raw_reply, reply_list
import settings as setting

bot = Bot(token=setting.API_TOKEN)
ADMIN_ID = int(setting.ADMIN_ID)
dispatcher = Dispatcher()


def buttons_keyboard(unique_id: int,
                     keyboard_type: Literal[
                         "accept", "complete", "reject", "unlock", "comf_or_regect", "exit_chat", "open_user_chat"] = "accept"
                     ) -> types.InlineKeyboardMarkup:
    """
    Формирует клавиатуру в зависимости от нужного варианта.
    'accept' - по умолчанию, кнопки Принять / Отменить.
    'complete' - кнопки Отменить / Закрыть.
    """

    if keyboard_type == "accept":
        buttons = [
            [types.InlineKeyboardButton(text="Принять заявку", callback_data=f"ticket_accept_{unique_id}"),
             types.InlineKeyboardButton(text="Отменить заявку", callback_data=f"ticket_canceled_{unique_id}"), ],
            [types.InlineKeyboardButton(text="Открыть чат с пользователем", callback_data=f"user-chat_{unique_id}"), ]]
    elif keyboard_type == "complete":
        buttons = [[types.InlineKeyboardButton(text="Отменить заявку", callback_data=f"ticket_canceled_{unique_id}"),
                    types.InlineKeyboardButton(text="Закрыть заявку",
                                               callback_data=f"ticket_completed_{unique_id}"), ], ]

    elif keyboard_type == "reject":
        buttons = [[types.InlineKeyboardButton(text="Отменить заявку",
                                               callback_data=f"ticket_usercancel_{unique_id}"), ], ]

    elif keyboard_type == "comf_or_regect":
        buttons = [[types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm"),
                    types.InlineKeyboardButton(text="Отменить", callback_data="reject"), ], ]

    elif keyboard_type == "exit_chat":
        buttons = [[types.InlineKeyboardButton(text="Закрыть чат", callback_data="exit_chat")]]

    elif keyboard_type == "open_user_chat":
        buttons = [[types.InlineKeyboardButton(text="Начать чат", callback_data="open_user_chat")]]

    else:
        buttons = [[types.InlineKeyboardButton(text="Разблокировать пользователя.",
                                               callback_data=f"user_unlock_{unique_id}", )]]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


async def generate_start_link(our_bot: Bot):
    return await create_start_link(our_bot, setting.ACCESS_KEY)


@dispatcher.callback_query(lambda call: call.data.startswith("user_"))
async def manage_users(callback: types.CallbackQuery):
    if not callback.data:
        return
    _, action, uid = callback.data.split("_")
    if action == "unlock":
        unblock_user(uid)
        setting.till_block_counter.pop(int(uid))
        await callback.message.edit_text(f"Пользователь {uid} разблокирован.")
        await bot.send_message(chat_id=uid, text="Вы были разблокированы администратором бота.")
    await callback.answer()


@dispatcher.callback_query(lambda call: call.data.startswith("ticket_"))
async def send_message_users(callback: types.CallbackQuery):
    if not callback.data:
        return
    _, status, ticket_id = callback.data.split("_")
    ticket = get_ticket_by_id(int(ticket_id))
    if not ticket:
        return
    if ticket.status == "rejected":
        await bot.send_message(chat_id=ADMIN_ID, text=f"Невозможно обрабатывать отмененную заявку.")
        await callback.answer()
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
        text=f"Новая заявка: \n{reply_text.as_html()}\nПод номером {ticket_id} создана.",
        reply_markup=buttons_keyboard(ticket_id),
    )


@dispatcher.callback_query(lambda call: call.data.startswith("user-chat_"))
async def chat_user(callback: types.CallbackQuery, state: FSMContext):
    ticket_id = callback.data.split("_")[1]
    user_uid = get_ticket_by_id(int(ticket_id)).user_uid
    await state.update_data(user_uid=user_uid)
    await bot.send_message(user_uid, text="Админ открыл чат.\n"
                                          "Чтобы начать общение нажмите кнопку.",
                           reply_markup=buttons_keyboard(user_uid, "open_user_chat"))
    await callback.message.reply("Введите сообщение для пользователя:")
    await state.set_state(AdminChatState.waiting_for_message)
    await callback.answer()


@dispatcher.message(AdminChatState.waiting_for_message)
async def waiting_for_admin_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_uid = data.get("user_uid")
    if message.chat.id == ADMIN_ID:
        await bot.send_message(user_uid, text=f"Сообщение от администратора:\n\n {message.text}\n\n"
                                              f"Введите сообщение чтобы ответить:")
    else:
        await bot.send_message(ADMIN_ID,
                               text=f"Сообщение от пользователя {message.from_user.first_name}:\n\n {message.text}",
                               reply_markup=buttons_keyboard(ADMIN_ID, "exit_chat"))


@dispatcher.callback_query(lambda call: call.data in ["exit_chat", "open_user_chat"])
async def exit_chat(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user_uid = data.get("user_uid")
    user_id = callback.message.chat.id
    await callback.answer()
    if callback.data == "exit_chat":
        if user_id == ADMIN_ID:
            await callback.message.reply("Чат закрыт.")
            await bot.send_message(user_uid, text="Чат закрыт. Ожидайте решения проблемы.",
                                   reply_markup=buttons_keyboard(ADMIN_ID, "exit_chat"))
        else:
            await callback.message.edit_text("Чат закрыт. Ожидайте решения проблемы.")
        await state.set_state(None)
        return
    if callback.data == "open_user_chat":
        await callback.message.reply("Чат открыт.\n"
                                     "Введите сообщение чтобы ответить:")
        await state.set_state(AdminChatState.waiting_for_message)


@dispatcher.message(Command("help"))
async def cmd_help(message: types.Message):
    if check_blocked(message.from_user.id) is True:
        return
    await message.answer(
        "Основные команды для работы:\n"
        "/register - команда для регистрации пользователя.\n"
        "/new_ticket - команда для создания новой заявки.\n"
        "/tickets - команда для проверки ваших заявок.\n"
        "/cancel - команда для отмены заявки <code>/cancel (номер тикета для отмены)</code>.\n",
        parse_mode=ParseMode.HTML,
    )


@dispatcher.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    if check_blocked(message.from_user.id) is True:
        await message.answer("Вы заблокированы. Обратитесь к администратору.")
        return
    if command.args == setting.ACCESS_KEY:
        is_admin = message.chat.id == ADMIN_ID
        await set_commands(is_admin)
        await message.answer(
            "Добро пожаловать в бот!\nДля продолжения пройдите регистрацию /register или воспользуйтесь "
            "помощью по командам /help."
        )
        return
    if message.chat.id not in setting.till_block_counter:
        setting.till_block_counter[message.from_user.id] = 5
    if setting.till_block_counter[message.from_user.id] > 0:
        await message.answer(
            f"Вы не предоставили ключ доступа к боту или ваш ключ неверен. "
            f"У вас осталось {setting.till_block_counter[message.from_user.id]} попыток до блокировки."
        )
        setting.till_block_counter[message.from_user.id] -= 1
    else:
        add_blocked_user(message.from_user.id, message.from_user.username)
        await message.answer("Вы были заблокированы. Обратитесь к администратору бота для разблокировки.")
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Пользователь {message.from_user.id} был заблокирован за 5 попыток запуска без ключа.",
            reply_markup=buttons_keyboard(message.from_user.id, "unlock"),
        )


@dispatcher.my_chat_member(filters.ChatMemberUpdatedFilter(member_status_changed=filters.JOIN_TRANSITION))
async def my_chat_member(message: types.Message) -> None:
    await message.answer("Я не работаю в группах.")
    await bot.leave_chat(message.chat.id)


@dispatcher.message(Command("register"))
async def cmd_register(message: types.Message, state: FSMContext) -> None:
    if check_blocked(message.from_user.id) is True:
        await message.answer("Вы заблокированы. Обратитесь к администратору.")
        return

    if check_user_registration(message.chat.id):
        await message.answer("Вы уже зарегистрированы.")
        return

    await message.reply("Введите ваши имя и фамилию.\nНапример: Иван Иванов.\n"
                        "Или используйте /next, для использования данных из телеграмм профиля.")
    await state.set_state(RegisterStates.first_and_last_name)


@dispatcher.message(RegisterStates.first_and_last_name)
async def process_name_and_department(message: types.Message, state: FSMContext) -> None:
    if message.text == "/next":
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        if first_name and last_name:
            await message.reply("Введите ваш отдел.\nНапример: Отдел разработки")
            await state.update_data(first_name=first_name, last_name=last_name)
            await state.set_state(RegisterStates.department)
            return
        await state.set_state(RegisterStates.first_and_last_name)
        await message.reply("Введите ваши имя и фамилию.\nНапример: Иван Иванов\n"
                            "Или используйте /next, для использования данных из телеграмм профиля.")
    first_and_last_name = message.text
    parts = first_and_last_name.split(" ")
    if len(parts) < 2:
        await message.reply("Неверный формат. Введите имя и фамилию.")
        return
    first_name = parts[0]
    last_name = parts[1]
    await state.update_data(first_name=first_name, last_name=last_name)
    await message.reply("Введите ваш отдел.\nНапример: Отдел разработки")
    await state.set_state(RegisterStates.department)


@dispatcher.message(RegisterStates.department)
async def process_department(message: types.Message, state: FSMContext) -> None:
    department = message.text
    if department is None:
        await message.reply("Неверный формат. Введите отдел.")
        return
    await state.update_data(department=department)
    data = await state.get_data()

    await message.reply(
        "Проверьте данные и подтвердите регистрацию.\n"
        f"Имя: {data.get('first_name')}\n"
        f"Фамилия: {data.get('last_name')}\n"
        f"Отдел: {data.get('department')}\n\n",
        reply_markup=buttons_keyboard(message.from_user.id, "comf_or_regect"),
    )
    await state.set_state(RegisterStates.confirm)


@dispatcher.callback_query(lambda call: call.data in ["confirm", "reject"])
async def process_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.data == "confirm":
        data = await state.get_data()
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        department = data.get("department")
        is_admin = callback.message.chat.id == ADMIN_ID

        if first_name is None or last_name is None or department is None or is_admin is None:
            await callback.message.reply("Ошибка: Не все данные были получены. Пожалуйста,"
                                         "попробуйте зарегистрироваться заново.")
            await state.set_state(None)
            return

        ans = await answer_register(callback.message, first_name, last_name, department, is_admin)
        if ans:
            await callback.message.edit_text(ans)
        await state.set_state(None)
    elif callback.data == "reject":
        await callback.message.edit_text("Регистрация отменена.")
        await state.set_state(None)


@dispatcher.message(Command("tickets"))
async def cmd_tickets(message: types.Message, command: CommandObject) -> None:
    if check_blocked(message.from_user.id) is True:
        await message.answer("Вы заблокированы. Обратитесь к администратору.")
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
async def cmd_start_ticket(message: types.Message, state: FSMContext) -> None:
    if check_blocked(message.from_user.id) is True:
        await message.answer("Вы заблокированы. Обратитесь к администратору.")
        return
    if not check_user_registration(message.chat.id) or not message.from_user:
        await message.answer("Вы не зарегистрированы в боте, введите команду /register.")
        return

    await message.reply("Введите кратко суть вашей проблемы:")
    await state.set_state(TicketStates.title)


@dispatcher.message(TicketStates.title)
async def process_title(message: types.Message, state: FSMContext) -> None:
    title = message.text
    await state.update_data(title=title)
    await message.reply("Теперь введите описание вашей проблемы:")
    await state.set_state(TicketStates.description)


@dispatcher.message(TicketStates.description)
async def process_description(message: types.Message, state: FSMContext) -> None:
    description = message.text
    user_id = message.chat.id

    data = await state.get_data()
    title = data.get("title")

    ticket_dict = new_ticket(description, title, user_id)
    reply_text = raw_reply(ticket_dict)
    ticket_id = add_ticket(ticket_dict)

    await admin_to_accept_button(reply_text, ticket_id)
    if user_id != ADMIN_ID:
        await message.reply(reply_text.as_html(), reply_markup=buttons_keyboard(ticket_id, "reject"))

    await state.set_state(None)


@dispatcher.message(Command("cancel"))
async def cmd_cancel_ticket(message: types.Message, command: CommandObject) -> None:
    if check_blocked(message.from_user.id) is True:
        await message.answer("Вы заблокированы. Обратитесь к администратору.")
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


@dispatcher.message(Command("check_admin"))
async def cmd_check_authority(message: types.Message) -> None:
    if check_blocked(message.from_user.id) is True:
        await message.answer("Вы заблокированы. Обратитесь к администратору.")
        return
    if message.chat.id != ADMIN_ID:
        await message.reply("Нет прав администратора.")
        return

    await message.reply("Права администратора подтверждены.")
    # Регистрация администратора в таблице Users если он не записан в базе.
    if check_user_registration(message.chat.id) or not message.chat.first_name or not message.chat.last_name:
        return
    await answer_register(message, message.chat.first_name, message.chat.last_name, "Admin", True)


@dispatcher.message(Command("block"))
async def cmd_block_user(message: types.Message, command: CommandObject) -> None:
    if message.chat.id != ADMIN_ID:
        await message.answer(f"Вы не являетесь администратором. Нет доступа.")
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
        await message.answer(f"Вы не являетесь администратором. Нет доступа.")
        return
    if command.args is None:
        await message.reply("Укажите UID пользователя для разблокировки.")
        if blocklist := all_blocked_users():
            for user in blocklist:
                await message.answer(f"{user[0]}: {user[1]}", reply_markup=buttons_keyboard(user[0], "unlock"))
        else:
            await message.answer("На данный момент нет заблокированных пользователей.")
            return
    if command.args:
        unblock_user(int(command.args))
        setting.till_block_counter.pop(int(command.args))
        await bot.send_message(chat_id=int(command.args), text="Вы были разблокированы администратором бота.")
    if not check_blocked(int(command.args)):
        await message.answer(f"Пользователь {int(command.args)} разблокирован.")


async def set_commands(is_admin):
    if is_admin:
        commands = [
            BotCommand(command="register", description="Команда для регистрации пользователя"),
            BotCommand(command="new_ticket", description="Команда для создания новой заявки"),
            BotCommand(command="tickets", description="Команда для проверки ваших заявок"),
            BotCommand(command="cancel", description="Команда для отмены заявки"),
            BotCommand(command="help", description="Справка по командам"),
            BotCommand(command="tickets", description="Команда для создания новой заявки"),
            BotCommand(command="check_admin", description="Команда для проверки статуса Admin"),
            BotCommand(command="block", description="Команда для блокировки пользователя"),
            BotCommand(command="unblock", description="Команда для разблокировки пользователя"),
        ]
        await bot.set_my_commands(commands, BotCommandScopeChat(chat_id=ADMIN_ID))

    else:
        commands = [
            BotCommand(command="register", description="Команда для регистрации пользователя"),
            BotCommand(command="new_ticket", description="Команда для создания новой заявки"),
            BotCommand(command="tickets", description="Команда для проверки ваших заявок"),
            BotCommand(command="cancel", description="Команда для отмены заявки"),
            BotCommand(command="help", description="Справка по командам"),
        ]
        await bot.set_my_commands(commands, BotCommandScopeDefault())


async def main():
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Бот запущен, приглашение работает по ссылке {await generate_start_link(bot)}",
    )
    await dispatcher.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    setting.setup_logging(log_file="bot.log")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка сервера!")
