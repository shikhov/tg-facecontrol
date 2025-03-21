# Telegram Face Control

Простой и надежный бот, реализующий капчу для телеграм-чатов.

<div align="center">
  <img class="logo" src="https://github.com/shikhov/tg-facecontrol/raw/main/media/pic.jpg" width="400px"/>
</div>

## Ключевые особенности
- не отвлекает участников своей работой, капча решается в личке с ботом
- удобен для пользователя — для прохождения теста достаточно нажать одну кнопку
- индивидуальные настройки капчи для каждого чата
- быстрое развертывание — заполнить конфигурационный файл и запустить докер-контейнер

## Запуск
- Создайте файл `config.toml` или отредактируйте прилагаемый `config.example`
- Запустите контейнер (для примера конфигурационный файл лежит в `/home/config.toml`):

  `docker run -d --restart=on-failure -v /home/config.toml:/etc/config.toml shikhov/tg-facecontrol`
- Добавьте бота в чат и сделайте его администратором
- Включите в чате вступление по заявкам (approve new members)
- Бот начнет отвечать на запросы на вступление в чат

Для изменения настроек достаточно отредактировать `config.toml` и перезапустить контейнер.

## Конфигурация

- `bot_token` – токен бота
- секция `[defaults]` – здесь описываются настройки, которые применяются ко всем чатам, если у них нет собственных
    - `emoji_list` - строка со списком эмоджи, которые будут использоваться в качестве вариантов ответа. Первым должен идти правильный ответ
    - `emoji_rowsize` - количество кнопок в строке (как они будут располагаться под сообщением). Число от 1 до 8
    - `welcome_text` - приветственное сообщение, содержащее капчу. Шаблон `%CHAT_TITLE%` в тексте будет заменен на имя чата
    - `success_text` - сообщение в случае успешного решения
    - `fail_text` - сообщение в случае неудачного решения
    - `error_text` - текст в случае какой-то иной ошибки
    - `timeout_text` - сообщение в случае истечения времени на решение капчи
    - `captcha_timeout` - время в секундах на решение капчи
    - `delete_joins` - удалять ли сообщения о входе новых участников
    - `logchatid` - ID чата для логирования попыток входов. Необязательное поле
- секции `[[groups]]` - файл должен содержать одну или несколько таких секций, в них описываются настройки самих чатов
    - `id` - ID чата. Единственное обязательное поле в секции
    - секция может содержать собственные настройки из перечисленных выше. Если какие-то из них отсутствуют, будут использованы настройки из секции `[defaults]`
    - если нужно выключить логирование для конкретного чата, переменную `logchatid` установить в 0

Все ID чатов должны быть целыми числами или строками, содержащими их. Бот будет работать только в чатах, указанных в конфигурации. При попытке добавить бота в любой другой чат, он будет немедленно выходить из него.

Пример файла `config.toml`:
```toml
bot_token = "your_bot_token"

[defaults]
emoji_list = "💎💩💩💩💩💩💩💩💩"
emoji_rowsize = 3
welcome_text = 'Для вступления в чат "%CHAT_TITLE%" нажмите на нужный значок'
success_text = "Верно! Добро пожаловать в наш чат!"
fail_text = "К сожалению, вы не прошли тест"
error_text = "⚠️ Произошла ошибка"
timeout_text = "К сожалению, вы не успели пройти тест за отведенное время"
captcha_timeout = 120
delete_joins = true
logchatid = -1001122334455

# HarryPotterChat
[[groups]]
id = -100123456789
delete_joins = false

# Basketball Fan Chat
[[groups]]
id = -100987654321
emoji_list = "🏀🎈🎹🍕"
emoji_rowsize = 4
welcome_text = "Нет времени объяснять, жмите на мяч. У вас есть 10 секунд"
captcha_timeout = 10
logchatid = -1002243669518888
```