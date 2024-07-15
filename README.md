# Flask_Dp_TelegramHelpDesk
Дипломный проект "Телеграм-бот HelpDesk" на Flask.
Рекомендуется версия Python 3.10.
Кроме зависимостей дополнительно можно использовать ruff (`pip install ruff`)

### Для установки зависимостей использовать команду:
`pip install -r requirements.txt`
### Перед запуском требуется создать файл .env на основе .env.sample из репозитория (не забудьте указать свои значения для переменных)
`cp .env.sample .env`
### Для запуска приложения использовать команду в папке проекта:
`python bot/bot.py`

###Основные команды для работы:
#### 1. /register - команда для регистрации пользователя.
#### 2. /new_ticket - команда для создания новой заявки, */new_ticket <опишите тут вашу проблему>*.
#### 3. /tickets - команда для проверки ваших заявок.
#### 4. /cancel - команда для отмены заявки */cancel <номер тикета для отмены>*.
#### 5. /complete - команда для самостоятельного закрытия заявки */complete <номер тикета для завершения>*.
